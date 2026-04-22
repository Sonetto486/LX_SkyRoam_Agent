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
  isHovered: boolean;
  day?: number;
  time?: string;
}

interface MapComponentProps {
  markers: Marker[];
  center: { lat: number; lng: number };
  zoom: number;
  viewMode?: 'day' | 'full';
  currentDay?: number;
}

const MapComponent: React.FC<MapComponentProps> = ({
  markers,
  center,
  zoom,
  viewMode = 'day',
  currentDay = 1
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const isMountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 更新标记的函数（使用 useCallback 避免重复创建）
  const updateMarkers = useCallback(() => {
    if (!mapLoaded || !mapInstanceRef.current || !isMountedRef.current) return;
    // 清除旧标记
    markersRef.current.forEach(marker => {
      try { mapInstanceRef.current.remove(marker); } catch (e) { }
    });
    markersRef.current = [];

    markers.forEach(marker => {
      try {
        const amapMarker = new window.AMap.Marker({
          position: [marker.position.lng, marker.position.lat],
          title: marker.name,
          label: { content: marker.name, direction: 'top' }
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

    if (markers.length > 0 && isMountedRef.current) {
      try {
        const positions = markers.map(m => [m.position.lng, m.position.lat]);
        mapInstanceRef.current.setFitView(positions, false, [50, 50, 50, 50]);
      } catch (e) { }
    }
  }, [markers, mapLoaded]);

  useEffect(() => {
    isMountedRef.current = true;
    abortControllerRef.current = new AbortController();

    const amapKey = process.env.REACT_APP_AMAP_KEY;
    if (!amapKey) {
      console.error('高德地图 API Key 未配置，请在 .env 文件中设置 REACT_APP_AMAP_KEY');
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
        if (isMountedRef.current) initMap();
      };
      script.onerror = () => {
        console.error('Failed to load AMap SDK');
        if (isMountedRef.current) setLoadError(true);
      };
      document.head.appendChild(script);

      abortControllerRef.current?.signal.addEventListener('abort', () => {
        if (script.parentNode) script.parentNode.removeChild(script);
      });
    };

    loadAMap();

    return () => {
      isMountedRef.current = false;
      abortControllerRef.current?.abort();
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.destroy();
        } catch (e) { }
        mapInstanceRef.current = null;
      }
      markersRef.current = [];
      if (mapRef.current) {
        mapRef.current.innerHTML = ''; // 彻底清空容器
      }
    };
  }, [center.lng, center.lat, zoom, updateMarkers]);

  // 监听中心点变化
  useEffect(() => {
    if (!mapLoaded || !mapInstanceRef.current || !isMountedRef.current) return;
    try {
      mapInstanceRef.current.setCenter([center.lng, center.lat]);
      updateMarkers();
    } catch (e) { }
  }, [center, mapLoaded, updateMarkers]);

  if (loadError) {
    return (
      <div className="map-container" ref={mapRef}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', background: '#f5f5f5', color: '#666', textAlign: 'center', padding: '20px' }}>
          <div>
            <h3>地图加载失败</h3>
            <p>请检查高德地图 API Key 配置</p>
            <p>中心坐标: {center.lat}, {center.lng}</p>
            <p>标记数量: {markers.length}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="map-container" style={{ position: 'relative' }}>
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
      {!mapLoaded && (
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: 10 }}>
          地图加载中...
        </div>
      )}
    </div>
  );
};

export default MapComponent;