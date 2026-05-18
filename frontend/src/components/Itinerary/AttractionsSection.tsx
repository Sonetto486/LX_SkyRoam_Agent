import React, { useState, useEffect } from 'react';
import { Card, List, Tag, Button, Space, Typography, Collapse, Rate, message, Spin, Tooltip, Popconfirm, Dropdown, Menu } from 'antd';
import {
  CameraOutlined,
  EnvironmentOutlined,
  StarOutlined,
  CarOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  SwapOutlined,
  CheckCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  StarFilled,
  UpOutlined,
  DownOutlined as MoveDownOutlined,
  EyeOutlined,
  CalendarOutlined
} from '@ant-design/icons';
import { authFetch } from '../../utils/auth';
import { buildApiUrl } from '../../config/api';
import './AttractionsSection.css';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface Attraction {
  name: string;
  type?: string;
  score?: number;
  address?: string;
  description?: string;
  coordinates?: { lat: number; lng: number };
  inSchedule?: boolean; // 是否已在日程中
  priority?: string; // 'must' | 'optional' | 'backup'
  id?: number | string; // 景点ID
  images?: string[]; // 景点图片（兼容旧字段）
  image_url?: string; // 单张图片URL（高德）
  photos?: string[]; // 图片URL数组（高德）
}

interface TravelAlternative {
  mode: string;
  mode_label: string;
  duration: number;
  distance: number;
}

interface RouteSegment {
  from: string;
  to: string;
  from_id?: number | string;
  to_id?: number | string;
  distance?: number;
  duration?: number;
  mode?: string;
  mode_label?: string;
  cost?: number;
  path?: any[]; // 路径点数组
  alternatives?: TravelAlternative[]; // 多种出行方案
}

interface AttractionsSectionProps {
  attractions: Attraction[];
  hotelAddress?: string;
  hotelCoordinates?: { lat: number; lng: number };
  planId?: number;
  dayDate?: string;
  currentDay?: number;
  totalDays?: number;
  onRouteOptimized?: (data: { date?: string; route_segments: RouteSegment[]; ordered_items?: any[] }) => void;
  onEditAttraction?: (index: number) => void;
  onDeleteAttraction?: (index: number) => void;
  onTogglePriority?: (index: number, priority: string) => void;
  onMoveAttraction?: (index: number, direction: 'up' | 'down') => void;
  onMoveToDay?: (index: number, targetDay: number) => void;
  onViewDetail?: (index: number) => void;
  onReorderAttractions?: (fromIndex: number, toIndex: number) => void; // 新增：拖拽交换顺序
}

const AttractionsSection: React.FC<AttractionsSectionProps> = ({
  attractions,
  hotelAddress,
  hotelCoordinates,
  planId,
  dayDate,
  currentDay,
  totalDays,
  onRouteOptimized,
  onEditAttraction,
  onDeleteAttraction,
  onTogglePriority,
  onMoveAttraction,
  onMoveToDay,
  onViewDetail,
  onReorderAttractions
}) => {
  const [routeSegments, setRouteSegments] = useState<RouteSegment[]>([]);
  const [loading, setLoading] = useState(false);
  const [optimized, setOptimized] = useState(false);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [lastAttractionsKey, setLastAttractionsKey] = useState<string>('');
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  useEffect(() => {
    // 只在景点列表真正变化时重置优化状态
    const currentKey = attractions.map(a => `${a.name}-${a.coordinates?.lat}-${a.coordinates?.lng}`).join(',');

    if (currentKey !== lastAttractionsKey && lastAttractionsKey !== '') {
      console.log('景点列表变化，重置优化状态');
      setOptimized(false);
      setRouteSegments([]);
    }
    setLastAttractionsKey(currentKey);
  }, [attractions, lastAttractionsKey]);

  const handleOptimizeRoute = async () => {
    if (!planId) {
      message.warning('无法获取行程ID');
      return;
    }

    if (attractions.length < 2) {
      message.warning('景点数量不足，至少需要2个景点才能优化路线');
      return;
    }

    setLoading(true);
    console.log('开始路径优化，planId:', planId, 'dayDate:', dayDate);
    console.log('景点列表:', attractions);

    try {
      // 使用第一个景点作为起点
      const firstAttraction = attractions[0];
      const startPoint = firstAttraction.coordinates ? {
        name: firstAttraction.name,
        coordinates: firstAttraction.coordinates
      } : null;

      console.log('起点:', startPoint);

      const requestBody = {
        date: dayDate,
        start_point: startPoint,
      };
      console.log('请求体:', requestBody);

      // 调用后端路径优化API
      const url = buildApiUrl(`/travel-plans/${planId}/optimize-route`);
      console.log('API URL:', url);

      const response = await authFetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      console.log('响应状态:', response.status, response.ok);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API错误响应:', errorText);
        throw new Error('路径优化失败: ' + errorText);
      }

      const data = await response.json();

      console.log('路线优化返回数据:', data);
      console.log('route_segments:', data.route_segments);
      console.log('route_segments长度:', data.route_segments?.length);
      console.log('success:', data.success);
      console.log('ordered_items:', data.ordered_items);

      if (data.success && data.route_segments && data.route_segments.length > 0) {
        setRouteSegments(data.route_segments);
        setOptimized(true);
        message.success(`路径优化完成，共 ${data.route_segments.length} 个路段`);

        console.log('设置routeSegments后，当前routeSegments:', data.route_segments);

        if (onRouteOptimized) {
          // 传递完整的数据结构，包含日期、路径段和有序景点列表
          onRouteOptimized({
            date: dayDate,
            route_segments: data.route_segments,
            ordered_items: data.ordered_items
          });
        }
      } else {
        console.log('没有route_segments或success为false');
        message.warning(data.message || '没有可优化的路径');
      }
    } catch (error: any) {
      console.error('路径优化失败:', error);
      message.error(error.message || '路径优化失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取出行方式图标
  const getModeIcon = (mode?: string) => {
    switch (mode) {
      case 'walking':
        return <span style={{ fontSize: '14px' }}>🚶</span>;
      case 'transit':
        return <span style={{ fontSize: '14px' }}>🚌</span>;
      case 'driving':
        return <CarOutlined style={{ fontSize: '14px' }} />;
      default:
        return <CarOutlined style={{ fontSize: '14px' }} />;
    }
  };

  // 获取优先级标签
  const getPriorityTag = (priority?: string) => {
    switch (priority) {
      case 'must':
        return <Tag color="red" icon={<StarFilled />}>必去</Tag>;
      case 'optional':
        return <Tag color="blue">可选</Tag>;
      case 'backup':
        return <Tag color="default">备选</Tag>;
      default:
        return <Tag color="blue">可选</Tag>;
    }
  };

  // 切换优先级
  const handleTogglePriority = (index: number, currentPriority?: string) => {
    if (!onTogglePriority) return;

    let newPriority: string;
    switch (currentPriority) {
      case 'must':
        newPriority = 'optional';
        break;
      case 'optional':
        newPriority = 'backup';
        break;
      case 'backup':
        newPriority = 'must';
        break;
      default:
        newPriority = 'must';
    }

    onTogglePriority(index, newPriority);
  };

  if (!attractions || attractions.length === 0) return null;

  // 获取景点图片（优先级：image_url > photos > images）
  const getAttractionImages = (attraction: Attraction): string[] => {
    if (attraction.image_url) return [attraction.image_url];
    if (attraction.photos && attraction.photos.length > 0) return attraction.photos.slice(0, 2);
    if (attraction.images && attraction.images.length > 0) return attraction.images.slice(0, 2);
    return [];
  };

  // 调试输出
  console.log('AttractionsSection渲染:', {
    attractionsCount: attractions.length,
    routeSegmentsCount: routeSegments.length,
    optimized,
    routeSegments
  });

  return (
    <Card
      title={
        <Space>
          <CameraOutlined />
          <span>景点列表</span>
          <Tag color="blue">{attractions.length} 个景点</Tag>
          {optimized && <Tag color="success" icon={<CheckCircleOutlined />}>已优化</Tag>}
        </Space>
      }
      extra={
        <Space>
          <Tooltip title="调整景点顺序后点击优化路线">
            <Button
              type="primary"
              size="small"
              icon={<SwapOutlined />}
              onClick={handleOptimizeRoute}
              loading={loading}
            >
              {loading ? '优化中...' : '路线优化'}
            </Button>
          </Tooltip>
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      {/* 起点提示 */}
      {attractions.length > 0 && (
        <Card size="small" style={{ marginBottom: 8, backgroundColor: '#f6ffed' }}>
          <Space>
            <Tag color="green">起点</Tag>
            <Text strong>{attractions[0].name}</Text>
            <Text type="secondary">（第一个景点）</Text>
            {attractions.length > 1 && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                使用上移按钮调整起点位置
              </Text>
            )}
          </Space>
        </Card>
      )}

      {/* 景点列表 */}
      <List
        dataSource={attractions}
        renderItem={(attraction, index) => (
          <div
            key={index}
            draggable={true}
            onDragStart={(e) => {
              setDraggingIndex(index);
              e.dataTransfer.effectAllowed = 'move';
              e.dataTransfer.setData('text/plain', index.toString());
            }}
            onDragEnd={() => {
              setDraggingIndex(null);
              setDragOverIndex(null);
            }}
            onDragOver={(e) => {
              e.preventDefault();
              e.dataTransfer.dropEffect = 'move';
              if (draggingIndex !== null && draggingIndex !== index) {
                setDragOverIndex(index);
              }
            }}
            onDragLeave={() => {
              setDragOverIndex(null);
            }}
            onDrop={(e) => {
              e.preventDefault();
              const fromIndex = parseInt(e.dataTransfer.getData('text/plain'));
              const toIndex = index;

              // 同一天内拖拽交换顺序
              if (!isNaN(fromIndex) && fromIndex !== toIndex && onReorderAttractions) {
                onReorderAttractions(fromIndex, toIndex);
              }

              setDraggingIndex(null);
              setDragOverIndex(null);
            }}
          >
            {/* 景点卡片 */}
            <List.Item style={{ border: 'none', padding: '8px 0' }}>
              <Card
                size="small"
                hoverable
                className={`attraction-card ${hoveredIndex === index ? 'hovered' : ''} ${draggingIndex === index ? 'dragging' : ''} ${dragOverIndex === index ? 'drag-over' : ''}`}
                style={{
                  width: '100%',
                  borderLeft: index === 0 ? '4px solid #52c41a' : '4px solid #1890ff',
                  cursor: 'grab',
                  opacity: draggingIndex === index ? 0.5 : 1,
                  transition: 'all 0.2s ease',
                  transform: dragOverIndex === index ? 'scale(1.02)' : 'none',
                  boxShadow: dragOverIndex === index ? '0 4px 12px rgba(24, 144, 255, 0.3)' : 'none'
                }}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                <div className="attraction-card-content">
                  <div className="attraction-info">
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Space>
                        <Tag color={index === 0 ? 'green' : 'blue'}>{index + 1}</Tag>
                        {index === 0 && <Tag color="green">起点</Tag>}
                        <Text strong>{attraction.name}</Text>
                        {attraction.inSchedule && (
                          <Tag color="green" style={{ fontSize: 10 }}>已在日程</Tag>
                        )}
                        {getPriorityTag(attraction.priority)}
                      </Space>

                      {attraction.type && (
                        <Tag color="blue" style={{ marginTop: 4 }}>{attraction.type}</Tag>
                      )}

                      {attraction.score && (
                        <Space style={{ marginTop: 4 }}>
                          <StarOutlined style={{ color: '#faad14' }} />
                          <Text>{attraction.score} 分</Text>
                        </Space>
                      )}

                      {attraction.address && (
                        <Paragraph style={{ margin: '4px 0', fontSize: 12, color: '#8c8c8c' }}>
                          <EnvironmentOutlined style={{ marginRight: 4 }} />
                          {attraction.address}
                        </Paragraph>
                      )}

                      {/* 景点图片缩略图 - 显示1-2张图片 */}
                      {getAttractionImages(attraction).length > 0 && (
                        <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                          {getAttractionImages(attraction).map((img, imgIdx) => (
                            <img
                              key={imgIdx}
                              src={img}
                              alt={`${attraction.name} ${imgIdx + 1}`}
                              style={{
                                width: 80,
                                height: 60,
                                objectFit: 'cover',
                                borderRadius: 4,
                                cursor: 'pointer'
                              }}
                              onClick={() => onViewDetail && onViewDetail(index)}
                              onError={(e) => {
                                // 图片加载失败时使用兜底图片
                                e.currentTarget.src = 'https://via.placeholder.com/80x60?text=No+Image';
                              }}
                            />
                          ))}
                        </div>
                      )}

                      {/* 查看详情折叠 */}
                      {(attraction.description || getAttractionImages(attraction).length > 1) && (
                        <Collapse
                          ghost
                          size="small"
                          style={{ marginTop: 8 }}
                          items={[{
                            key: '1',
                            label: <Text type="secondary" style={{ fontSize: 12 }}>查看详情</Text>,
                            children: (
                              <div>
                                {attraction.description && (
                                  <Paragraph style={{ margin: '0 0 8px 0', fontSize: 12, color: '#666' }}>
                                    {attraction.description}
                                  </Paragraph>
                                )}
                                {getAttractionImages(attraction).length > 1 && (
                                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                                    {getAttractionImages(attraction).slice(1, 4).map((img, imgIndex) => (
                                      <img
                                        key={imgIndex}
                                        src={img}
                                        alt={`${attraction.name} ${imgIndex + 2}`}
                                        style={{
                                          width: 60,
                                          height: 45,
                                          objectFit: 'cover',
                                          borderRadius: 4
                                        }}
                                        onError={(e) => {
                                          // 图片加载失败时使用兜底图片
                                          e.currentTarget.src = 'https://via.placeholder.com/60x45?text=No+Image';
                                        }}
                                      />
                                    ))}
                                  </div>
                                )}
                              </div>
                            )
                          }]}
                        />
                      )}
                    </Space>
                  </div>

                  {/* 操作按钮（hover显示） */}
                    <div className={`attraction-actions ${hoveredIndex === index ? 'visible' : ''}`}>
                      {/* 查看详情 */}
                      {onViewDetail && (
                        <Tooltip title="查看详情">
                          <Button
                            type="text"
                            size="small"
                            icon={<EyeOutlined />}
                            onClick={() => onViewDetail(index)}
                          />
                        </Tooltip>
                      )}
                      {/* 上移按钮 */}
                      {onMoveAttraction && index > 0 && (
                        <Tooltip title="上移">
                          <Button
                            type="text"
                            size="small"
                            icon={<UpOutlined />}
                            onClick={() => onMoveAttraction(index, 'up')}
                          />
                        </Tooltip>
                      )}
                      {/* 下移按钮 */}
                      {onMoveAttraction && index < attractions.length - 1 && (
                        <Tooltip title="下移">
                          <Button
                            type="text"
                            size="small"
                            icon={<MoveDownOutlined />}
                            onClick={() => onMoveAttraction(index, 'down')}
                          />
                        </Tooltip>
                      )}
                      {/* 移动到其他天数 */}
                      {onMoveToDay && totalDays && totalDays > 1 && (
                        <Dropdown
                          overlay={
                            <Menu>
                              {Array.from({ length: totalDays }, (_, i) => i + 1).filter(day => day !== currentDay).map(day => (
                                <Menu.Item
                                  key={day}
                                  onClick={() => onMoveToDay(index, day)}
                                >
                                  <CalendarOutlined /> Day {day}
                                </Menu.Item>
                              ))}
                            </Menu>
                          }
                          trigger={['click']}
                        >
                          <Tooltip title="移动到其他天数">
                            <Button
                              type="text"
                              size="small"
                              icon={<CalendarOutlined />}
                            />
                          </Tooltip>
                        </Dropdown>
                      )}
                      {/* 优先级切换 */}
                      {onTogglePriority && (
                        <Tooltip title="切换优先级">
                          <Button
                            type="text"
                            size="small"
                            icon={<StarFilled />}
                            onClick={() => handleTogglePriority(index, attraction.priority)}
                          />
                        </Tooltip>
                      )}
                      {onEditAttraction && (
                        <Tooltip title="编辑">
                          <Button
                            type="text"
                            size="small"
                            icon={<EditOutlined />}
                            onClick={() => onEditAttraction(index)}
                          />
                        </Tooltip>
                      )}
                      {onDeleteAttraction && (
                        <Popconfirm
                          title="确定删除此景点？"
                          okText="删除"
                          cancelText="取消"
                          onConfirm={() => onDeleteAttraction(index)}
                        >
                          <Tooltip title="删除">
                            <Button
                              type="text"
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                            />
                          </Tooltip>
                        </Popconfirm>
                      )}
                    </div>
                </div>
              </Card>
            </List.Item>

            {/* 显示到下一个景点的路线信息 */}
            {(() => {
              const shouldShow = index < attractions.length - 1 && routeSegments[index];
              if (index === 0) {
                console.log(`交通卡片检查 [index=${index}]:`, {
                  'index < attractions.length - 1': index < attractions.length - 1,
                  'routeSegments[index]': routeSegments[index],
                  'shouldShow': shouldShow,
                  'routeSegments': routeSegments
                });
              }
              return shouldShow;
            })() && (
              <Card
                key={`route-${index}`}
                size="small"
                className="route-segment-card"
                style={{
                  margin: '4px 0 8px 0',
                  backgroundColor: '#e6f7ff',
                  border: '1px dashed #1890ff'
                }}
              >
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  {/* 主要出行方式 */}
                  <Space split={<Text type="secondary">→</Text>} size={8}>
                    <Text type="secondary">
                      {getModeIcon(routeSegments[index].mode)} {routeSegments[index].mode_label || routeSegments[index].mode || '交通'}
                    </Text>
                    {routeSegments[index].duration && (
                      <Text type="secondary">
                        <ClockCircleOutlined /> {routeSegments[index].duration}分钟
                      </Text>
                    )}
                    {routeSegments[index].distance && (
                      <Text type="secondary">
                        <EnvironmentOutlined /> {routeSegments[index].distance}公里
                      </Text>
                    )}
                    {routeSegments[index].cost && (
                      <Text type="warning">
                        <DollarOutlined /> ¥{routeSegments[index].cost}
                      </Text>
                    )}
                  </Space>

                  {/* 其他出行方案（折叠显示） */}
                  {(() => {
                    const segment = routeSegments[index];
                    if (!segment?.alternatives || segment.alternatives.length === 0) return null;
                    return (
                      <Collapse ghost size="small">
                        <Panel header="查看其他出行方案" key="alternatives">
                          <Space direction="vertical" size={4} style={{ width: '100%' }}>
                            {segment.alternatives.map((alt, altIndex) => (
                              <Space key={altIndex} size={8}>
                                {getModeIcon(alt.mode)}
                                <Text type="secondary">{alt.mode_label}</Text>
                                <Text type="secondary">
                                  <ClockCircleOutlined /> {alt.duration}分钟
                                </Text>
                                <Text type="secondary">
                                  <EnvironmentOutlined /> {alt.distance}公里
                                </Text>
                              </Space>
                            ))}
                          </Space>
                        </Panel>
                      </Collapse>
                    );
                  })()}
                </Space>
              </Card>
            )}
          </div>
        )}
      />
    </Card>
  );
};

export default AttractionsSection;