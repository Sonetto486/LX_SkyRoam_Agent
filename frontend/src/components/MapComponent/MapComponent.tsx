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
  time?: string;
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
}

const MapComponent: React.FC<MapComponentProps> = ({
  markers,
  center,
  zoom,
  viewMode = 'day',
  currentDay = 1,
  routeSegments = []
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

    // 清除旧标记
    markersRef.current.forEach(marker => {
      try { mapInstanceRef.current.remove(marker); } catch (e) { }
    });
    markersRef.current = [];

    // 清除旧路线
    polylineRef.current.forEach(polyline => {
      try { mapInstanceRef.current.remove(polyline); } catch (e) { }
    });
    polylineRef.current = [];

    // 绘制直线（辅助函数）
    const drawStraightLine = (dayMarkers: Marker[], isCurrentDay: boolean) => {
      const path = dayMarkers.map(m => [m.position.lng, m.position.lat]);

      const polyline = new window.AMap.Polyline({
        path: path,
        strokeColor: isCurrentDay ? '#1890ff' : '#999999',
        strokeWeight: isCurrentDay ? 4 : 2,
        strokeOpacity: isCurrentDay ? 0.9 : 0.5,
        strokeStyle: isCurrentDay ? 'solid' : 'dashed',
        lineJoin: 'round',
        lineCap: 'round',
        showDir: true
      });
      mapInstanceRef.current.add(polyline);
      polylineRef.current.push(polyline);
    };

    // 添加标记点
    markers.forEach(marker => {
      try {
        const amapMarker = new window.AMap.Marker({
          position: [marker.position.lng, marker.position.lat],
          title: marker.name,
          label: {
            content: `<div class="map-marker-label">${marker.name}</div>`,
            direction: 'top'
          }
        });
        const infoWindow = new window.AMap.InfoWindow({
          content: `
            <div style="padding: 10px; max-width: 200px;">
              <h4 style="margin:0 0 8px 0;color:#1890ff;">${marker.name}</h4>
              <p style="margin:0 0 4px 0;color:#666;">${marker.address}</p>
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

    // 绘制路线：按天分组
    const markersByDay: Record<number, Marker[]> = {};
    markers.forEach(m => {
      const day = m.day || 1;
      if (!markersByDay[day]) markersByDay[day] = [];
      markersByDay[day].push(m);
    });

    // 为每天绘制路线
    Object.entries(markersByDay).forEach(([day, dayMarkers]) => {
      if (dayMarkers.length < 2) return;

      const dayNum = parseInt(day);
      const isCurrentDay = viewMode === 'full' || dayNum === currentDay;

      // 查找当天的路线段信息
      const dayRouteSegments = routeSegments.find((seg: DayRouteData) =>
        seg.date === day || seg.ordered_items?.some((item: any) =>
          dayMarkers.some(m => m.id === item.id)
        )
      );

      // 如果有后端返回的路径点，使用它们绘制路线
      if (dayRouteSegments && dayRouteSegments.route_segments) {
        console.log('使用后端返回的路径点绘制路线');

        dayRouteSegments.route_segments.forEach((segment: any, segIndex: number) => {
          if (segment.path && segment.path.length > 0) {
            // 使用后端返回的详细路径点
            const path = segment.path.map((point: any) => [point.lng, point.lat]);

            const polyline = new window.AMap.Polyline({
              path: path,
              strokeColor: isCurrentDay ? '#1890ff' : '#999999',
              strokeWeight: isCurrentDay ? 4 : 2,
              strokeOpacity: isCurrentDay ? 0.9 : 0.5,
              strokeStyle: isCurrentDay ? 'solid' : 'dashed',
              lineJoin: 'round',
              lineCap: 'round',
              showDir: true
            });

            mapInstanceRef.current.add(polyline);
            polylineRef.current.push(polyline);

            // 添加方向箭头
            const arrowCount = Math.min(3, Math.floor(path.length / 5));
            for (let i = 0; i < path.length - 1; i += Math.floor(path.length / (arrowCount + 1))) {
              const startPoint = path[i];
              const endPoint = path[Math.min(i + 1, path.length - 1)];

              if (!startPoint || !endPoint) continue;

              const midLng = (startPoint[0] + endPoint[0]) / 2;
              const midLat = (startPoint[1] + endPoint[1]) / 2;

              const dx = endPoint[0] - startPoint[0];
              const dy = endPoint[1] - startPoint[1];
              const angle = Math.atan2(dy, dx) * 180 / Math.PI;

              const arrowMarker = new window.AMap.Marker({
                position: [midLng, midLat],
                icon: new window.AMap.Icon({
                  size: new window.AMap.Size(16, 16),
                  image: 'data:image/svg+xml;base64,' + btoa(`
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
                      <path d="M8 2 L14 8 L8 14 L8 10 L2 10 L2 6 L8 6 Z"
                            fill="${isCurrentDay ? '#1890ff' : '#999999'}"
                            transform="rotate(${angle} 8 8)"/>
                    </svg>
                  `),
                  imageSize: new window.AMap.Size(16, 16)
                }),
                offset: new window.AMap.Pixel(-8, -8),
                zIndex: 100
              });

              mapInstanceRef.current.add(arrowMarker);
              markersRef.current.push(arrowMarker);
            }
          } else {
            // 如果没有路径点，使用直线连接相邻景点
            const fromMarker = dayMarkers[segIndex];
            const toMarker = dayMarkers[segIndex + 1];
            if (fromMarker && toMarker) {
              drawStraightLine([fromMarker, toMarker], isCurrentDay);
            }
          }
        });
      } else {
        // 如果没有后端路径点，尝试使用前端驾车路线规划
        if (isCurrentDay && window.AMap.Driving) {
          console.log('使用驾车路线规划，景点数量:', dayMarkers.length);

          const driving = new window.AMap.Driving({
            policy: window.AMap.DrivingPolicy.LEAST_TIME,
            hideMarkers: true,
            autoFitView: false
          });

          const waypoints = dayMarkers.length > 2
            ? dayMarkers.slice(1, -1).map(m =>
                new window.AMap.LngLat(m.position.lng, m.position.lat)
              )
            : [];

          const origin = new window.AMap.LngLat(dayMarkers[0].position.lng, dayMarkers[0].position.lat);
          const destination = new window.AMap.LngLat(
            dayMarkers[dayMarkers.length - 1].position.lng,
            dayMarkers[dayMarkers.length - 1].position.lat
          );

          // 根据是否有途经点，决定调用方式
          if (waypoints.length > 0) {
            driving.search(
              origin,
              destination,
              { waypoints: waypoints },
              (status: string, result: any) => {
                if (status === 'complete' && result.routes && result.routes.length > 0) {
                  console.log('驾车路线规划成功，开始绘制路线');

                  const route = result.routes[0];
                  const path: any[] = [];

                  route.steps.forEach((step: any) => {
                    step.path.forEach((point: any) => {
                      path.push([point.lng, point.lat]);
                    });
                  });

                  const actualPolyline = new window.AMap.Polyline({
                    path: path,
                    strokeColor: '#1890ff',
                    strokeWeight: 4,
                    strokeOpacity: 0.9,
                    strokeStyle: 'solid',
                    lineJoin: 'round',
                    lineCap: 'round',
                    showDir: true
                  });

                  mapInstanceRef.current.add(actualPolyline);
                  polylineRef.current.push(actualPolyline);
                } else {
                  console.error('驾车路线规划失败:', status, result);
                  drawStraightLine(dayMarkers, isCurrentDay);
                }
              }
            );
          } else {
            // 没有途经点时，只传起点、终点和回调函数
            driving.search(
              origin,
              destination,
              (status: string, result: any) => {
                if (status === 'complete' && result.routes && result.routes.length > 0) {
                  console.log('驾车路线规划成功，开始绘制路线');

                  const route = result.routes[0];
                  const path: any[] = [];

                  route.steps.forEach((step: any) => {
                    step.path.forEach((point: any) => {
                      path.push([point.lng, point.lat]);
                    });
                  });

                  const actualPolyline = new window.AMap.Polyline({
                    path: path,
                    strokeColor: '#1890ff',
                    strokeWeight: 4,
                    strokeOpacity: 0.9,
                    strokeStyle: 'solid',
                    lineJoin: 'round',
                    lineCap: 'round',
                    showDir: true
                  });

                  mapInstanceRef.current.add(actualPolyline);
                  polylineRef.current.push(actualPolyline);
                } else {
                  console.error('驾车路线规划失败:', status, result);
                  drawStraightLine(dayMarkers, isCurrentDay);
                }
              }
            );
          }

          drivingRef.current = driving;
        } else {
          if (!window.AMap.Driving) {
            console.warn('Driving 插件未加载，使用直线连接');
          }
          drawStraightLine(dayMarkers, isCurrentDay);
        }
      }
    });

    // 自适应视图
    if (markers.length > 0 && isMountedRef.current) {
      try {
        const positions = markers.map(m => [m.position.lng, m.position.lat]);
        mapInstanceRef.current.setFitView(positions, false, [50, 50, 50, 50]);
      } catch (e) { }
    }
  }, [markers, mapLoaded, viewMode, currentDay]);

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
