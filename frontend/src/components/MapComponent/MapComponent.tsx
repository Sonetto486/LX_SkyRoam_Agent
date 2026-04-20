import React, { useEffect, useRef } from 'react';
import './MapComponent.css';

interface Marker {
  id: number;
  name: string;
  position: { lat: number; lng: number };
  address: string;
  isHovered: boolean;
}

interface MapComponentProps {
  markers: Marker[];
  center: { lat: number; lng: number };
  zoom: number;
}

const MapComponent: React.FC<MapComponentProps> = ({ markers, center, zoom }) => {
  const mapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 这里可以集成高德地图、百度地图或其他地图 API
    // 由于是模拟环境，我们使用一个简单的地图占位符
    if (mapRef.current) {
      // 实际项目中，这里会初始化地图实例
      // 例如：AMap.init() 或 BMap.init()
      console.log('Map initialized with center:', center, 'zoom:', zoom);
      console.log('Markers:', markers);
    }
  }, [center, zoom, markers]);

  return (
    <div className="map-container" ref={mapRef}>
      {/* 地图占位符 */}
      <div className="map-placeholder">
        <div className="map-center" style={{ 
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center'
        }}>
          <h3>地图组件</h3>
          <p>中心坐标: {center.lat}, {center.lng}</p>
          <p>缩放级别: {zoom}</p>
          <p>标记数量: {markers.length}</p>
          <div style={{ marginTop: 20, fontSize: 12, color: '#666' }}>
            实际项目中，这里会集成真实的地图 API
          </div>
        </div>
        
        {/* 模拟标记 */}
        {markers.map((marker) => (
          <div 
            key={marker.id}
            className={`map-marker ${marker.isHovered ? 'hovered' : ''}`}
            style={{
              position: 'absolute',
              left: `${(marker.position.lng - center.lng) * 1000 + 50}%`,
              top: `${(center.lat - marker.position.lat) * 1000 + 50}%`,
              transform: 'translate(-50%, -50%)'
            }}
          >
            <div className="marker-content">
              <div className="marker-title">{marker.name}</div>
              <div className="marker-address">{marker.address}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MapComponent;
