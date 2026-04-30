import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Input, List, Card, Tag, Spin, Empty, message, Button, Popconfirm } from 'antd';
import { SearchOutlined, EnvironmentOutlined, StarOutlined, StarFilled, PhoneOutlined, GlobalOutlined } from '@ant-design/icons';
import { authFetch } from '../../utils/auth';
import './LocationSearch.css';

const { Search } = Input;

// 简单的 debounce hook
function useDebounce<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<NodeJS.Timeout>();

  return useCallback((...args: Parameters<T>) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      callback(...args);
    }, delay);
  }, [callback, delay]) as T;
}

interface LocationResult {
  id?: string;
  name: string;
  address?: string;
  location?: { lat: number; lng: number };
  category?: string;
  distance?: number;
  tel?: string;
  rating?: number;
  cost?: number;
  type?: string;
}

interface FavoriteLocation {
  id: number;
  name: string;
  address?: string;
  coordinates?: { lat: number; lng: number };
  category?: string;
  phone?: string;
  poi_id?: string;
  source?: string;
  notes?: string;
}

interface LocationSearchProps {
  city?: string;
  category?: string;
  onSelect?: (location: LocationResult) => void;
  onFavoriteChange?: () => void;
  showFavorites?: boolean;
  style?: React.CSSProperties;
}

const LocationSearch: React.FC<LocationSearchProps> = ({
  city,
  category,
  onSelect,
  onFavoriteChange,
  showFavorites = true,
  style,
}) => {
  const [keyword, setKeyword] = useState('');
  const [results, setResults] = useState<LocationResult[]>([]);
  const [favorites, setFavorites] = useState<FavoriteLocation[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'search' | 'favorites'>('search');
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());

  // 获取收藏列表
  const fetchFavorites = useCallback(async () => {
    try {
      const response = await authFetch('/api/v1/locations/favorites');
      if (response.ok) {
        const data = await response.json();
        setFavorites(data);
        setFavoriteIds(new Set(data.filter((f: FavoriteLocation) => f.poi_id).map((f: FavoriteLocation) => f.poi_id!)));
      }
    } catch (error) {
      console.error('获取收藏列表失败:', error);
    }
  }, []);

  useEffect(() => {
    if (showFavorites) {
      fetchFavorites();
    }
  }, [showFavorites, fetchFavorites]);

  // 搜索地点的核心函数
  const doSearch = useCallback(async (value: string) => {
    if (!value.trim()) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const response = await authFetch('/api/v1/locations/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keyword: value,
          city,
          category,
          page: 1,
          page_size: 20,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setResults(data.results || []);
      } else {
        message.error('搜索失败');
      }
    } catch (error) {
      console.error('搜索失败:', error);
      message.error('搜索失败');
    } finally {
      setLoading(false);
    }
  }, [city, category]);

  // 使用 debounce 包装搜索函数
  const searchLocations = useDebounce(doSearch, 500);

  // 添加收藏
  const addFavorite = async (location: LocationResult) => {
    try {
      const response = await authFetch('/api/v1/locations/favorites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: location.name,
          address: location.address,
          coordinates: location.location,
          category: location.category,
          phone: location.tel,
          poi_id: location.id,
          source: 'amap',
        }),
      });

      if (response.ok) {
        message.success('已添加收藏');
        fetchFavorites();
        onFavoriteChange?.();
      } else {
        const error = await response.json();
        message.error(error.detail || '收藏失败');
      }
    } catch (error) {
      console.error('收藏失败:', error);
      message.error('收藏失败');
    }
  };

  // 删除收藏
  const removeFavorite = async (favoriteId: number) => {
    try {
      const response = await authFetch(`/api/v1/locations/favorites/${favoriteId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        message.success('已取消收藏');
        fetchFavorites();
        onFavoriteChange?.();
      } else {
        message.error('取消收藏失败');
      }
    } catch (error) {
      console.error('取消收藏失败:', error);
      message.error('取消收藏失败');
    }
  };

  // 检查是否已收藏
  const isFavorite = (poiId?: string) => {
    return poiId ? favoriteIds.has(poiId) : false;
  };

  // 获取分类标签颜色
  const getCategoryColor = (cat?: string) => {
    switch (cat) {
      case 'attraction':
        return 'green';
      case 'restaurant':
        return 'orange';
      case 'hotel':
        return 'blue';
      case 'shopping':
        return 'purple';
      default:
        return 'default';
    }
  };

  // 获取分类标签文本
  const getCategoryText = (cat?: string) => {
    switch (cat) {
      case 'attraction':
        return '景点';
      case 'restaurant':
        return '餐厅';
      case 'hotel':
        return '酒店';
      case 'shopping':
        return '购物';
      default:
        return '其他';
    }
  };

  // 渲染地点卡片
  const renderLocationCard = (location: LocationResult | FavoriteLocation, isFavoriteItem = false) => {
    const poiId = 'id' in location && typeof location.id === 'string' ? location.id : ('poi_id' in location ? location.poi_id : undefined);
    const coordinates = 'location' in location ? location.location : ('coordinates' in location ? location.coordinates : undefined);
    const phone = 'tel' in location ? location.tel : ('phone' in location ? location.phone : undefined);
    const cat = location.category;

    return (
      <List.Item key={poiId || ('id' in location ? location.id : undefined)}>
        <Card
          size="small"
          className="location-card"
          hoverable
          onClick={() => onSelect?.(location as LocationResult)}
          actions={[
            showFavorites && (
              isFavoriteItem ? (
                <Popconfirm
                  title="确定取消收藏？"
                  onConfirm={(e) => {
                    e?.stopPropagation();
                    removeFavorite((location as FavoriteLocation).id);
                  }}
                  onCancel={(e) => e?.stopPropagation()}
                >
                  <StarFilled
                    className="favorite-icon active"
                    onClick={(e) => e.stopPropagation()}
                  />
                </Popconfirm>
              ) : (
                <StarOutlined
                  className={`favorite-icon ${isFavorite(poiId) ? 'active' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (isFavorite(poiId)) {
                      message.info('该地点已收藏');
                    } else {
                      addFavorite(location as LocationResult);
                    }
                  }}
                />
              )
            ),
          ].filter(Boolean)}
        >
          <Card.Meta
            title={
              <div className="location-title">
                <span>{location.name}</span>
                {cat && (
                  <Tag color={getCategoryColor(cat)} style={{ marginLeft: 8 }}>
                    {getCategoryText(cat)}
                  </Tag>
                )}
              </div>
            }
            description={
              <div className="location-info">
                {location.address && (
                  <div className="info-item">
                    <EnvironmentOutlined /> {location.address}
                  </div>
                )}
                {phone && (
                  <div className="info-item">
                    <PhoneOutlined /> {phone}
                  </div>
                )}
                {'rating' in location && location.rating && (
                  <div className="info-item rating">
                    评分: {location.rating.toFixed(1)}
                  </div>
                )}
                {'cost' in location && location.cost && (
                  <div className="info-item cost">
                    ¥{location.cost}/人
                  </div>
                )}
                {'distance' in location && location.distance && (
                  <div className="info-item distance">
                    {location.distance < 1000
                      ? `${location.distance}米`
                      : `${(location.distance / 1000).toFixed(1)}公里`}
                  </div>
                )}
              </div>
            }
          />
        </Card>
      </List.Item>
    );
  };

  return (
    <div className="location-search" style={style}>
      {showFavorites && (
        <div className="search-tabs">
          <Button
            type={activeTab === 'search' ? 'primary' : 'text'}
            onClick={() => setActiveTab('search')}
          >
            搜索地点
          </Button>
          <Button
            type={activeTab === 'favorites' ? 'primary' : 'text'}
            onClick={() => setActiveTab('favorites')}
          >
            我的收藏 ({favorites.length})
          </Button>
        </div>
      )}

      {activeTab === 'search' ? (
        <>
          <Search
            placeholder="搜索地点名称..."
            allowClear
            enterButton={<SearchOutlined />}
            size="large"
            value={keyword}
            onChange={(e) => {
              setKeyword(e.target.value);
              searchLocations(e.target.value);
            }}
            loading={loading}
          />

          <div className="search-results">
            {loading ? (
              <div className="loading-container">
                <Spin tip="搜索中..." />
              </div>
            ) : results.length > 0 ? (
              <List
                dataSource={results}
                renderItem={(item) => renderLocationCard(item)}
              />
            ) : keyword ? (
              <Empty description="未找到相关地点" />
            ) : (
              <Empty description="输入关键词搜索地点" />
            )}
          </div>
        </>
      ) : (
        <div className="favorites-list">
          {favorites.length > 0 ? (
            <List
              dataSource={favorites}
              renderItem={(item) => renderLocationCard(item, true)}
            />
          ) : (
            <Empty description="暂无收藏地点" />
          )}
        </div>
      )}
    </div>
  );
};

export default LocationSearch;
