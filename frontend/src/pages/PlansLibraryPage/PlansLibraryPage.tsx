import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Card, Typography, Space, Tag, Button, Row, Col, Empty, Spin, Pagination, Input, DatePicker, Rate, Alert } from 'antd';
import { CalendarOutlined, EnvironmentOutlined, EyeOutlined, HistoryOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';

const { Title, Paragraph, Text } = Typography;

type TravelPlan = {
  id: number;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  status: string;
  score: number;
  created_at: string;
  is_public?: boolean;
};

const PlansLibraryPage: React.FC = () => {
  const navigate = useNavigate();
  const latestReq = useRef(0);
  const [plans, setPlans] = useState<TravelPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [keyword, setKeyword] = useState('');
  const [minScore, setMinScore] = useState<number | undefined>();
  const [dateRange, setDateRange] = useState<any[]>([]);
  const pageSize = 100;

  const toDateStr = (d: any): string => {
    if (!d) return '';
    try {
      const dj = (typeof d.isValid === 'function') ? d : dayjs(d);
      if (!dj.isValid()) return '';
      return dj.format('YYYY-MM-DD');
    } catch {
      return '';
    }
  };

  const fetchPlans = useCallback(async (keywordOverride?: string) => {
    const reqId = ++latestReq.current;
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.set('skip', String((currentPage - 1) * pageSize));
      params.set('limit', String(pageSize));
      const keywordToUse = keywordOverride !== undefined ? keywordOverride : keyword;
      if (keywordToUse && keywordToUse.trim()) params.set('keyword', keywordToUse.trim());
      if (typeof minScore === 'number') params.set('min_score', String(minScore));
      if (dateRange && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
        const fromStr = toDateStr(dateRange[0]);
        const toStr = toDateStr(dateRange[1]);
        if (fromStr) params.set('travel_from', fromStr);
        if (toStr) params.set('travel_to', toStr);
      }

      const response = await fetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLANS_PUBLIC + `?${params.toString()}`));
      if (!response.ok) throw new Error('获取公开计划失败');
      const data = await response.json();
      if (reqId !== latestReq.current) return;

      const list = Array.isArray(data?.plans) ? data.plans : (Array.isArray(data) ? data : []);
      const totalCount = typeof data?.total === 'number' ? data.total : (Array.isArray(data) ? data.length : 0);
      setPlans(list);
      setTotal(totalCount);
    } catch {
      if (reqId !== latestReq.current) return;
      setPlans([]);
      setTotal(0);
    } finally {
      if (reqId === latestReq.current) setLoading(false);
    }
  }, [currentPage, dateRange, keyword, minScore]);

  useEffect(() => {
    fetchPlans();
  }, [fetchPlans]);

  const getStatusTag = (status: string) => {
    const statusMap = {
      draft: { color: 'default', text: '草稿' },
      generating: { color: 'processing', text: '生成中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
      archived: { color: 'default', text: '已归档' }
    } as Record<string, { color: string; text: string }>;
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const handleReset = () => {
    setKeyword('');
    setMinScore(undefined);
    setDateRange([]);
    setCurrentPage(1);
    latestReq.current += 1;
    setTimeout(() => fetchPlans(''), 0);
  };

  const handleSearch = (value: string) => {
    setKeyword(value);
    setCurrentPage(1);
    fetchPlans(value);
  };

  return (
    <div className="plans-library-page" style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <HistoryOutlined style={{ marginRight: 8 }} />
          计划库
        </Title>
        <Alert type="info" showIcon message="公开计划为只读视图，点击查看按钮会跳转到对应的我的行程区。" style={{ marginTop: 8 }} />
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Input.Search
            placeholder="关键词（标题/目的地/描述）"
            allowClear
            style={{ width: 280 }}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={handleSearch}
            enterButton
          />
          <DatePicker.RangePicker value={dateRange as any} onChange={(range) => setDateRange(range || [])} />
          <Button onClick={handleReset}>重置</Button>
        </Space>
      </Card>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}><Text>加载中...</Text></div>
        </div>
      ) : plans.length === 0 ? (
        <Card>
          <Empty description="暂无公开计划" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </Card>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            {plans.map((plan) => (
              <Col xs={24} sm={12} lg={8} key={plan.id}>
                <Card
                  className="travel-card glass-card"
                  hoverable
                  actions={[
                    <Button
                      key="view"
                      type="text"
                      icon={<EyeOutlined />}
                      onClick={() => navigate(`/itineraries/${plan.id}`)}
                    >
                      查看
                    </Button>
                  ]}
                >
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Title level={4} style={{ margin: 0, flex: 1 }}>{plan.title}</Title>
                      <Space>
                        <Tag color="purple">ID: {plan.id}</Tag>
                        {plan.is_public && <Tag color="cyan">公开</Tag>}
                      </Space>
                    </div>
                    <Space>
                      <Tag color="blue" icon={<EnvironmentOutlined />}>{plan.destination}</Tag>
                      <Tag color="green" icon={<CalendarOutlined />}>{plan.duration_days} 天</Tag>
                    </Space>
                    <div>
                      <Text type="secondary">{new Date(plan.start_date).toLocaleDateString('zh-CN')} - {new Date(plan.end_date).toLocaleDateString('zh-CN')}</Text>
                    </div>
                    <div>
                      <Space>
                        {getStatusTag(plan.status)}
                        {typeof plan.score === 'number' && (
                          <>
                            <Tag color="orange">评分: {plan.score.toFixed(1)}</Tag>
                            <Rate disabled allowHalf value={plan.score} style={{ fontSize: 14 }} />
                          </>
                        )}
                      </Space>
                    </div>
                    <div>
                      <Text type="secondary" style={{ fontSize: '12px' }}>创建时间: {new Date(plan.created_at).toLocaleString('zh-CN')}</Text>
                    </div>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Pagination
              current={currentPage}
              total={total}
              pageSize={pageSize}
              onChange={setCurrentPage}
              showSizeChanger={false}
              showQuickJumper
              showTotal={(t, r) => `第 ${r[0]}-${r[1]} 条，共 ${t} 条`}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default PlansLibraryPage;
