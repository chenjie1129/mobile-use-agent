#!/usr/bin/env python3
"""
geo.py - 本地地理位置获取模块 (GpsInfo 注入)

火山引擎 Mobile Use Agent 的 GpsInfo 参数格式 (英文逗号分隔):
    "经度,纬度,海拔,速度,方位角,定位精度"
    示例: "116.397128,39.916527,50,0,0,10"
    - 经度/纬度: WGS-84 坐标系 (必填)
    - 海拔: 单位米 (m)
    - 速度: 单位米/秒 (m/s)
    - 方位角: 相对正北顺时针角度 (deg), 0~360
    - 定位精度: 水平误差半径 (m), 越小越精准

获取策略 (自动降级):
    1. macOS CoreLocation 系统定位 - 米级精度, 含海拔/速度/方位角
       需要运行脚本的终端 App 拥有定位权限:
       系统设置 > 隐私与安全性 > 定位服务 > (终端 / iTerm / WorkBuddy)
    2. IP 定位 - 城市级精度 (ip-api.com / ipinfo.io / ipapi.co)
       注意: 全部选用 WGS-84 坐标系的服务, 避免国内地图服务的
       GCJ-02/BD-09 偏移坐标系导致注入位置偏移。

隐私设计:
    本模块只提供"获取"能力; 是否获取由调用方 (CLI) 在每次发起
    任务前向用户征求同意, 获取结果 (来源/坐标/精度) 会明确告知用户。
"""

import json
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional

# IP 定位水平误差半径 (城市级, 约 10 km)
IP_LOCATION_ACCURACY = 10000.0


@dataclass
class LocationInfo:
    """统一的位置信息"""

    latitude: float          # 纬度 (WGS-84)
    longitude: float         # 经度 (WGS-84)
    altitude: float = 0.0    # 海拔 (m)
    speed: float = 0.0       # 速度 (m/s)
    course: float = 0.0      # 方位角 (deg, 相对正北顺时针)
    accuracy: float = 0.0    # 水平精度 (m)
    source: str = ""         # 来源描述
    address: str = ""        # 地址描述 (IP 定位时为城市名)


# ========================
# 格式化
# ========================


def format_gps_info(loc: LocationInfo) -> str:
    """转换为火山引擎 GpsInfo 格式: "经度,纬度,海拔,速度,方位角,定位精度" """
    return (
        f"{loc.longitude:.6f},{loc.latitude:.6f},"
        f"{loc.altitude:.0f},{loc.speed:.1f},{loc.course:.0f},{loc.accuracy:.0f}"
    )


def describe_location(loc: LocationInfo) -> str:
    """生成人类可读的位置描述"""
    lat_str = (
        f"北纬 {loc.latitude:.6f}" if loc.latitude >= 0 else f"南纬 {abs(loc.latitude):.6f}"
    )
    lon_str = (
        f"东经 {loc.longitude:.6f}" if loc.longitude >= 0 else f"西经 {abs(loc.longitude):.6f}"
    )
    desc = f"{loc.address}, " if loc.address else ""
    desc += f"{lat_str}, {lon_str}"
    acc = f", 精度 ±{loc.accuracy:.0f}m" if loc.accuracy > 0 else ""
    return f"{desc} (来源: {loc.source}{acc})"


# ========================
# 获取方式 1: macOS CoreLocation
# ========================


def get_location_corelocation(
    timeout: float = 15.0, verbose: bool = True
) -> Optional[LocationInfo]:
    """通过 macOS CoreLocation 获取精确位置

    无权限 / 超时 / 非 macOS / 依赖缺失时返回 None,
    由上层降级到 IP 定位。
    """
    if sys.platform != "darwin":
        return None

    try:
        import objc
        from Foundation import NSObject, NSRunLoop, NSDate, NSDefaultRunLoopMode
        from CoreLocation import (
            CLLocationManager,
            kCLAuthorizationStatusNotDetermined,
            kCLAuthorizationStatusDenied,
            kCLAuthorizationStatusRestricted,
        )
    except ImportError:
        if verbose:
            print("[定位] 未安装 pyobjc-framework-CoreLocation, 跳过系统定位")
        return None

    # 定位服务总开关
    if not CLLocationManager.locationServicesEnabled():
        if verbose:
            print("[定位] 系统定位服务未开启")
        return None

    status = CLLocationManager.authorizationStatus()
    if status in (kCLAuthorizationStatusDenied, kCLAuthorizationStatusRestricted):
        if verbose:
            print(
                "[定位] 终端未获得定位权限 "
                "(系统设置 > 隐私与安全性 > 定位服务)"
            )
        return None

    class LocationDelegate(NSObject):
        # 注意: 不重写 init (函数内定义的类无法使用 objc.super() 零参数形式,
        # pyobjc 会为实例提供 Python 属性存储), 状态在 alloc().init() 后设置。

        def locationManager_didUpdateLocations_(self, manager, locations):
            if locations:
                self.location = locations[-1]

        def locationManager_didFailWithError_(self, manager, error):
            self.error = error

        def locationManager_didChangeAuthorization_(self, manager, status):
            # 授权被明确拒绝时提前终止等待, 不傻等到超时
            if status in (kCLAuthorizationStatusDenied, kCLAuthorizationStatusRestricted):
                self.error = "定位权限被拒绝"

    manager = CLLocationManager.alloc().init()
    delegate = LocationDelegate.alloc().init()
    delegate.location = None  # CLLocation 对象
    delegate.error = None
    manager.setDelegate_(delegate)

    if status == kCLAuthorizationStatusNotDetermined:
        # 触发系统授权弹窗 (由终端 App 承接)
        manager.requestWhenInUseAuthorization()

    manager.startUpdatingLocation()

    # 驱动 runloop 等待回调 (定位回调经由 runloop 投递)
    deadline = time.time() + timeout
    while time.time() < deadline:
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            NSDefaultRunLoopMode, NSDate.dateWithTimeIntervalSinceNow_(0.3)
        )
        if delegate.location is not None or delegate.error is not None:
            break

    manager.stopUpdatingLocation()

    if delegate.error is not None or delegate.location is None:
        return None

    loc = delegate.location
    coord = loc.coordinate()
    speed = loc.speed()               # 无效时为 -1.0
    course = loc.course()             # 无效时为 -1.0
    h_acc = loc.horizontalAccuracy()  # 无效时为 -1.0
    v_acc = loc.verticalAccuracy()    # 无效时为 -1.0

    return LocationInfo(
        latitude=float(coord.latitude),
        longitude=float(coord.longitude),
        altitude=float(loc.altitude()) if v_acc >= 0 else 0.0,
        speed=float(speed) if speed >= 0 else 0.0,
        course=float(course) if course >= 0 else 0.0,
        accuracy=float(h_acc) if h_acc >= 0 else 0.0,
        source="macOS 系统定位 (CoreLocation)",
    )


# ========================
# 获取方式 2: IP 定位 (城市级)
# ========================


def _http_get_json(url: str, timeout: float) -> Optional[dict]:
    req = urllib.request.Request(
        url, headers={"User-Agent": "mobile-use-agent-cli/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_location_ip(timeout: float = 8.0) -> Optional[LocationInfo]:
    """通过 IP 定位获取大致位置 (城市级, WGS-84)

    依次尝试多个公共 IP 定位服务, 全部失败返回 None。
    """
    errors = []

    # --- 1) ip-api.com (支持中文城市名) ---
    try:
        data = _http_get_json(
            "http://ip-api.com/json/?lang=zh-CN"
            "&fields=status,message,lat,lon,city,regionName,country",
            timeout,
        )
        if data.get("status") == "success":
            addr = " ".join(
                filter(None, [data.get("country"), data.get("regionName"), data.get("city")])
            )
            return LocationInfo(
                latitude=float(data["lat"]),
                longitude=float(data["lon"]),
                accuracy=IP_LOCATION_ACCURACY,
                source="IP 定位 (ip-api.com, 城市级)",
                address=addr,
            )
        errors.append(f"ip-api: {data.get('message', 'unknown')}")
    except Exception as e:
        errors.append(f"ip-api: {e}")

    # --- 2) ipinfo.io ---
    try:
        data = _http_get_json("https://ipinfo.io/json", timeout)
        loc = data.get("loc", "")
        if "," in loc:
            lat, lon = loc.split(",", 1)
            addr = " ".join(
                filter(None, [data.get("country"), data.get("region"), data.get("city")])
            )
            return LocationInfo(
                latitude=float(lat),
                longitude=float(lon),
                accuracy=IP_LOCATION_ACCURACY,
                source="IP 定位 (ipinfo.io, 城市级)",
                address=addr,
            )
        errors.append("ipinfo: missing loc field")
    except Exception as e:
        errors.append(f"ipinfo: {e}")

    # --- 3) ipapi.co ---
    try:
        data = _http_get_json("https://ipapi.co/json/", timeout)
        if data.get("latitude") is not None and data.get("longitude") is not None:
            addr = " ".join(
                filter(None, [data.get("country_name"), data.get("region"), data.get("city")])
            )
            return LocationInfo(
                latitude=float(data["latitude"]),
                longitude=float(data["longitude"]),
                accuracy=IP_LOCATION_ACCURACY,
                source="IP 定位 (ipapi.co, 城市级)",
                address=addr,
            )
        errors.append("ipapi: missing coordinates")
    except Exception as e:
        errors.append(f"ipapi: {e}")

    for err in errors:
        print(f"  [IP定位] {err}")
    return None


# ========================
# 统一入口
# ========================


def get_location(verbose: bool = True, timeout: float = 15.0) -> Optional[LocationInfo]:
    """获取当前位置: CoreLocation 优先, 失败自动降级 IP 定位"""
    loc = get_location_corelocation(timeout=timeout, verbose=verbose)
    if loc is not None:
        return loc
    if verbose:
        print("[定位] 系统定位不可用, 降级为 IP 定位 (城市级精度)...")
    return get_location_ip(timeout=8.0)


def ask_location_permission() -> bool:
    """询问用户是否允许获取当前位置 (每次任务前由 CLI 调用)"""
    try:
        ans = input("是否允许获取当前位置并注入云手机 GPS? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes")


def acquire_gps(verbose: bool = True) -> Optional[str]:
    """获取当前位置并告知用户结果, 返回 GpsInfo 字符串

    Returns:
        GpsInfo 字符串 (如 "116.397128,39.916527,50,0,0,10"); 失败返回 None
    """
    loc = get_location(verbose=verbose)
    if loc is None:
        if verbose:
            print("[定位] 获取失败, 本次任务不注入 GpsInfo")
        return None

    gps_str = format_gps_info(loc)
    if verbose:
        print(f"[定位] 已获取: {describe_location(loc)}")
        print(f'[定位] GpsInfo 注入值: "{gps_str}"')
    return gps_str


if __name__ == "__main__":
    # 独立测试: python geo.py
    print("=" * 50)
    print("  地理位置获取测试")
    print("=" * 50)
    gps = acquire_gps()
    if gps:
        print(f"\nGpsInfo: {gps}")
    else:
        print("\n未获取到位置")
