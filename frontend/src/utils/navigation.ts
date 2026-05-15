// 导航工具函数

interface NavigationParams {
  name: string;
  city?: string;
  address?: string;
  coordinates?: { lat: number; lng: number };
}

/**
 * 构建带城市前缀的完整地址
 * 确保地址能被地图应用正确识别
 */
const buildFullAddress = (name: string, address?: string, city?: string): string => {
  // 如果地址已经包含城市信息，直接返回
  if (address && city && address.includes(city)) {
    return address;
  }

  // 构建完整地址：城市 + 名称 + 地址
  const parts: string[] = [];

  if (city) {
    parts.push(city);
  }

  parts.push(name);

  if (address) {
    parts.push(address);
  }

  return parts.join(' ');
};

/**
 * 打开高德地图导航
 * 使用高德地图 URI API 进行导航跳转
 */
export const openAmapNavigation = (params: NavigationParams): void => {
  const { name, city, address, coordinates } = params;
  let url = 'https://uri.amap.com/navigation?';

  if (coordinates) {
    // 优先使用坐标（更精确），同时提供完整地址作为名称
    const fullAddress = buildFullAddress(name, address, city);
    url += `to=${coordinates.lng},${coordinates.lat},${encodeURIComponent(fullAddress)}`;
  } else {
    // 无坐标时使用完整地址
    const fullAddress = buildFullAddress(name, address, city);
    url += `to=${encodeURIComponent(fullAddress)}`;
  }

  url += '&mode=car&policy=1&coordinate=gaode';

  window.open(url, '_blank');
};

/**
 * 打开百度地图导航
 * 使用百度地图 API 进行导航跳转
 */
export const openBaiduNavigation = (params: NavigationParams): void => {
  const { name, city, address, coordinates } = params;
  let url = 'https://api.map.baidu.com/direction?';

  if (coordinates) {
    // 优先使用坐标（更精确），同时提供完整地址作为名称
    const fullAddress = buildFullAddress(name, address, city);
    url += `destination=latlng:${coordinates.lat},${coordinates.lng}|name:${encodeURIComponent(fullAddress)}`;
  } else {
    // 无坐标时使用完整地址
    const fullAddress = buildFullAddress(name, address, city);
    url += `destination=${encodeURIComponent(fullAddress)}`;
  }

  url += '&mode=driving&coord_type=gcj02&output=html';

  window.open(url, '_blank');
};

/**
 * 拷贝地址到剪贴板
 * 支持现代浏览器 API 和旧版浏览器 fallback
 */
export const copyAddress = async (name: string, address?: string, city?: string): Promise<string> => {
  const fullAddress = buildFullAddress(name, address, city);

  try {
    // 使用现代 Clipboard API
    await navigator.clipboard.writeText(fullAddress);
    return fullAddress;
  } catch {
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = fullAddress;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    return fullAddress;
  }
};