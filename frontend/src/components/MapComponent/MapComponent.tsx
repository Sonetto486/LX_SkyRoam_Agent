import React, { useEffect, useRef, useState, useCallback } from 'react';
import './MapComponent.css';

declare global {
  interface Window {
    AMap: any;
  }
}

interface Marker {
  id: number | string;
  name: string;
  position: { lat: number; lng: number };
  address: string;
  isHovered?: boolean;
  day?: number;
  date?: string;  // 日期字符串，用于路线匹配
  time?: string;
  isHotel?: boolean;  // 标记为酒店，不参与路线绘制
  // 景点指标字段
  score?: number;      // 评分
  type?: string;       // 景点类型
  price?: number;      // 门票价格
}

interface RouteSegment {
  from_id: number;
  to_id: number;
  distance: number;
  duration: number;
  mode: string;
  path?: Array<{ lng: number; lat: number }>;  // 路径点
}

interface DayRouteData {
  date: string;
  ordered_items?: any[];
  route_segments?: RouteSegment[];
}

interface MapComponentProps {
  markers: Marker[];
  center: { lat: number; lng: number };
  zoom: number;
  viewMode?: 'day' | 'full';
  currentDay?: number;
  routeSegments?: DayRouteData[];
  fitRouteTrigger?: number;  // 用于触发地图视野调整
}

const MapComponent: React.FC<MapComponentProps> = ({
  markers,
  center,
  zoom,
  viewMode = 'day',
  currentDay = 1,
  routeSegments = [],
  fitRouteTrigger = 0
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const polylineRef = useRef<any[]>([]);
  const drivingRef = useRef<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const isMountedRef = useRef(true);

  // 更新标记和路线
  const updateMarkers = useCallback(() => {
    if (!mapLoaded || !mapInstanceRef.current || !isMountedRef.current) return;

    // 清除所有旧标记 - 使用 clearMap() 确保完全清理
    try {
      mapInstanceRef.current.clearMap();
      console.log('地图已完全清理');
    } catch (e) {
      console.error('清除地图失败:', e);
    }
    markersRef.current = [];
    polylineRef.current = [];

    // 绘制直线（辅助函数）
    const drawStraightLine = (dayMarkers: Marker[], isCurrentDay: boolean) => {
      const path = dayMarkers.map(m => [m.position.lng, m.position.lat]);

      const polyline = new window.AMap.Polyline({
        path: path,
        strokeColor: '#1890ff',  // 统一蓝色
        strokeWeight: isCurrentDay ? 4 : 2,
        strokeOpacity: isCurrentDay ? 0.9 : 0.6,
        strokeStyle: 'solid',
        lineJoin: 'round',
        lineCap: 'round',
        showDir: true  // 使用高德地图原生箭头，自动指向路径方向
      });
      mapInstanceRef.current.add(polyline);
      polylineRef.current.push(polyline);
    };

    // 添加标记点
    markers.forEach(marker => {
      try {
        // 酒店标记使用特殊样式
        const labelContent = marker.isHotel
          ? `<div class="map-marker-label" style="background:#722ed1;color:#fff;border-color:#722ed1;">🏨 ${marker.name}</div>`
          : `<div class="map-marker-label">${marker.name}</div>`;

        const amapMarker = new window.AMap.Marker({
          position: [marker.position.lng, marker.position.lat],
          title: marker.name,
          label: {
            content: labelContent,
            direction: 'top'
          }
        });
        const infoWindow = new window.AMap.InfoWindow({
          content: `
            <div style="padding: 10px; max-width: 200px;">
              <h4 style="margin:0 0 8px 0;color:${marker.isHotel ? '#722ed1' : '#1890ff'};">
                ${marker.isHotel ? '🏨 ' : ''}${marker.name}
              </h4>
              <p style="margin:0 0 4px 0;color:#666;">${marker.address}</p>
              ${marker.isHotel ? '<p style="margin:0;color:#722ed1;">住宿推荐</p>' : ''}
              ${marker.score ? `<p style="margin:0 0 4px 0;color:#faad14;">⭐ ${marker.score} 分</p>` : ''}
              ${marker.type ? `<p style="margin:0 0 4px 0;color:#52c41a;">📍 ${marker.type}</p>` : ''}
              ${marker.price ? `<p style="margin:0 0 4px 0;color:#ff4d4f;">💰 ¥${marker.price}</p>` : ''}
              ${marker.time ? `<p style="margin:0;color:#999;">时间: ${marker.time}</p>` : ''}
              ${marker.day ? `<p style="margin:0;color:#999;">第 ${marker.day} 天</p>` : ''}
            </div>
          `,
          offset: new window.AMap.Pixel(0, -30)
        });
        amapMarker.on('click', () => {
          infoWindow.open(mapInstanceRef.current, amapMarker.getPosition());
        });
        mapInstanceRef.current.add(amapMarker);
        markersRef.current.push(amapMarker);
      } catch (e) { }
    });

    // 绘制路线：按天分组（排除酒店标记）
    const markersByDay: Record<number, Marker[]> = {};
    markers.forEach(m => {
      // 酒店标记不参与路线绘制
      if (m.isHotel) return;

      const day = m.day || 1;
      if (!markersByDay[day]) markersByDay[day] = [];
      markersByDay[day].push(m);
    });

    // 为每天绘制路线 - 只有单天模式才绘制路线
    if (viewMode === 'day') {
      Object.entries(markersByDay).forEach(([day, dayMarkers]) => {
        if (dayMarkers.length < 2) return;

        const dayNum = parseInt(day);
        const isCurrentDay = dayNum === currentDay;

      // 获取当天的日期字符串（从第一个marker获取）
      const dayDateString = dayMarkers[0]?.date;

      // 查找当天的路线段信息 - 改进匹配逻辑
      // 1. 先尝试按日期字符串匹配
      // 2. 如果没有匹配，尝试按景点ID匹配
      const dayRouteSegments = routeSegments.find((seg: DayRouteData) => {
        // 优先按日期字符串匹配
        if (dayDateString && seg.date === dayDateString) {
          return true;
        }
        // 检查是否有ordered_items可以用于匹配
        if (seg.ordered_items && seg.ordered_items.length > 0) {
          return seg.ordered_items.some((item: any) =>
            dayMarkers.some(m => m.id === item.id)
          );
        }
        // 检查route_segments中的from_id/to_id是否匹配
        if (seg.route_segments && seg.route_segments.length > 0) {
          return seg.route_segments.some((segment: any) =>
            dayMarkers.some(m => m.id === segment.from_id || m.id === segment.to_id)
          );
        }
        return false;
      });

      // 如果有后端返回的路径点，使用它们绘制路线
      if (dayRouteSegments && dayRouteSegments.route_segments) {
        console.log('使用后端返回的路径点绘制路线，路径段数量:', dayRouteSegments.route_segments.length);
        console.log('路径段详情:', dayRouteSegments.route_segments);

        dayRouteSegments.route_segments.forEach((segment: any, segIndex: number) => {
          console.log(`处理路径段 ${segIndex}:`, segment);
          if (segment.path && segment.path.length > 0) {
            // 使用后端返回的详细路径点
            const path = segment.path.map((point: any) => [point.lng, point.lat]);
            console.log(`路径段 ${segIndex} 有 ${path.length} 个路径点`);

            const polyline = new window.AMap.Polyline({
              path: path,
              strokeColor: '#1890ff',  // 统一蓝色
              strokeWeight: isCurrentDay ? 4 : 2,
              strokeOpacity: isCurrentDay ? 0.9 : 0.6,
              strokeStyle: 'solid',
              lineJoin: 'round',
              lineCap: 'round',
              showDir: true  // 使用高德地图原生箭头，自动指向路径方向
            });

            mapInstanceRef.current.add(polyline);
            polylineRef.current.push(polyline);
          } else {
            // 如果没有路径点，使用直线连接相邻景点
            console.log(`路径段 ${segIndex} 没有路径点，使用直线连接`);
            const fromMarker = dayMarkers.find(m => m.id === segment.from_id);
            const toMarker = dayMarkers.find(m => m.id === segment.to_id);
            if (fromMarker && toMarker) {
              drawStraightLine([fromMarker, toMarker], isCurrentDay);
            }
          }
        });
      } else {
        // 如果没有后端路径点，使用直线连接（前端驾车路线规划可能失败）
        if (isCurrentDay) {
          console.log('没有找到路线段数据，使用直线连接景点，景点数量:', dayMarkers.length);
          drawStraightLine(dayMarkers, isCurrentDay);
        }
      }
    });
    } // end of if (viewMode === 'day')

    // 自适应视图 - 根据模式调整视野
    if (isMountedRef.current && mapInstanceRef.current) {
      try {
        if (viewMode === 'full') {
          // 全程模式：使用已添加的标记覆盖物调整视野，确保所有地标可见
          if (markersRef.current.length > 0) {
            mapInstanceRef.current.setFitView(markersRef.current, false, [50, 50, 50, 50]);
            console.log('全程模式：使用标记覆盖物调整视野，标记数量:', markersRef.current.length);
          }
        } else if (polylineRef.current.length > 0) {
          // 单天模式：使用路线调整视野
          mapInstanceRef.current.setFitView(polylineRef.current, false, [50, 50, 50, 50]);
          console.log('单天模式：使用路线调整视野，路线数量:', polylineRef.current.length);
        } else if (markersRef.current.length > 0) {
          // 单天模式无路线：使用标记覆盖物
          mapInstanceRef.current.setFitView(markersRef.current, false, [50, 50, 50, 50]);
          console.log('单天模式：使用标记覆盖物调整视野，标记数量:', markersRef.current.length);
        }
      } catch (e) {
        console.error('自适应视图失败:', e);
      }
    }
  }, [markers, mapLoaded, viewMode, currentDay, routeSegments]);

  // 更新地图中心点
  useEffect(() => {
    if (mapLoaded && mapInstanceRef.current && center) {
      try {
        mapInstanceRef.current.setCenter([center.lng, center.lat]);
      } catch (e) {
        console.error('Failed to set map center:', e);
      }
    }
  }, [center.lng, center.lat, mapLoaded]);

  useEffect(() => {
    isMountedRef.current = true;

    const amapKey = process.env.REACT_APP_AMAP_KEY;
    if (!amapKey) {
      console.error('高德地图 API Key 未配置');
      if (isMountedRef.current) setLoadError(true);
      return;
    }

    const initMap = () => {
      if (!mapRef.current || !isMountedRef.current) return;
      try {
        const instance = new window.AMap.Map(mapRef.current, {
          center: [center.lng, center.lat],
          zoom: zoom,
          viewMode: '2D',
          lang: 'zh_cn'
        });
        mapInstanceRef.current = instance;
        instance.on('complete', () => {
          if (isMountedRef.current) {
            setMapLoaded(true);
            updateMarkers();

            // 地图加载完成后，调整视野以包含所有标记点
            // 延迟执行，确保 markers 已更新
            setTimeout(() => {
              if (markersRef.current.length > 0 && mapInstanceRef.current) {
                try {
                  mapInstanceRef.current.setFitView(markersRef.current, false, [50, 50, 50, 50]);
                  console.log('初始地图视野已调整，包含', markersRef.current.length, '个标记点');
                } catch (e) {
                  console.error('初始视野调整失败:', e);
                }
              }
            }, 100);
          }
        });
      } catch (error) {
        console.error('Failed to initialize AMap:', error);
        if (isMountedRef.current) setLoadError(true);
      }
    };

    const loadAMap = () => {
      if (window.AMap) {
        initMap();
        return;
      }

      const script = document.createElement('script');
      script.src = `https://webapi.amap.com/maps?v=2.0&key=${amapKey}`;
      script.async = true;
      script.onload = () => {
        console.log('高德地图加载成功，开始加载 Driving 插件');

        // 动态加载 Driving 插件
        window.AMap.plugin('AMap.Driving', () => {
          console.log('Driving 插件加载成功');
          if (isMountedRef.current) initMap();
        });
      };
      script.onerror = () => {
        console.error('Failed to load AMap SDK');
        if (isMountedRef.current) setLoadError(true);
      };
      document.head.appendChild(script);
    };

    loadAMap();

    return () => {
      isMountedRef.current = false;
      if (mapInstanceRef.current) {
        try { mapInstanceRef.current.destroy(); } catch (e) { }
        mapInstanceRef.current = null;
      }
      markersRef.current = [];
      polylineRef.current = [];
    };
  }, [zoom]);

  // 监听标记变化
  useEffect(() => {
    updateMarkers();
  }, [markers, mapLoaded, viewMode, currentDay, updateMarkers]);

  // 路线优化成功后，调整地图视野让用户清晰看到路线
  useEffect(() => {
    if (fitRouteTrigger > 0 && mapLoaded && mapInstanceRef.current) {
      console.log('路线优化完成，调整地图视野，fitRouteTrigger:', fitRouteTrigger);

      // 使用已绘制的 polyline 来调整视野
      if (polylineRef.current.length > 0) {
        try {
          // setFitView 接收覆盖物数组，自动调整视野包含所有覆盖物
          mapInstanceRef.current.setFitView(polylineRef.current, false, [60, 60, 60, 60]);
          console.log('地图视野已调整，包含', polylineRef.current.length, '条路线');
        } catch (e) {
          console.error('调整地图视野失败:', e);
        }
      } else if (markersRef.current.length > 0) {
        // 如果没有路线，使用标记覆盖物调整视野
        try {
          mapInstanceRef.current.setFitView(markersRef.current, false, [60, 60, 60, 60]);
          console.log('地图视野已调整，包含', markersRef.current.length, '个标记点');
        } catch (e) {
          console.error('调整地图视野失败:', e);
        }
      }
    }
  }, [fitRouteTrigger, mapLoaded, markers]);

  if (loadError) {
    return (
      <div className="map-container" ref={mapRef}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', background: '#f5f5f5', color: '#666', textAlign: 'center', padding: '20px' }}>
          <div>
            <h3>地图加载失败</h3>
            <p>请检查高德地图 API Key 配置</p>
            <p>中心坐标: {center.lat}, {center.lng}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="map-container" style={{ position: 'relative' }}>
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
      {!mapLoaded && (
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' }}>
          地图加载中...
        </div>
      )}
    </div>
  );
};

export default MapComponent;
