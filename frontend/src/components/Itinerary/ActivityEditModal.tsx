import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, DatePicker, TimePicker, message, Tabs, Tag, Switch, Row, Col } from 'antd';
import { EnvironmentOutlined, CalendarOutlined, PhoneOutlined, GlobalOutlined, ClockCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import LocationSearch from './LocationSearch';
import './ActivityEditModal.css';

const { TextArea } = Input;
const { Option } = Select;

// 活动类型
const ACTIVITY_TYPES = [
  { value: 'attraction', label: '景点' },
  { value: 'restaurant', label: '餐厅' },
  { value: 'hotel', label: '酒店' },
  { value: 'transport', label: '交通' },
  { value: 'shopping', label: '购物' },
  { value: 'entertainment', label: '娱乐' },
  { value: 'other', label: '其他' },
];

// 优先级选项
const PRIORITY_OPTIONS = [
  { value: 'must', label: '必去', color: 'red' },
  { value: 'optional', label: '可选', color: 'blue' },
  { value: 'backup', label: '备选', color: 'default' },
];

// 服务设施选项
const FACILITY_OPTIONS = [
  '停车场', '餐厅', 'WiFi', '洗手间', '母婴室', '无障碍设施', '行李寄存', '充电站'
];

interface Activity {
  id?: number;
  title: string;
  description?: string;
  item_type: string;
  start_time?: string;
  end_time?: string;
  location?: string;
  address?: string;
  coordinates?: { lat: number; lng: number };
  details?: any;
  images?: string[];
  opening_hours?: { weekday?: string; weekend?: string };
  phone?: string;
  website?: string;
  facilities?: string[];
  priority?: string;
}

interface ActivityEditModalProps {
  visible: boolean;
  activity?: Activity | null;
  date?: string;
  startDate?: string;
  endDate?: string;
  onCancel: () => void;
  onOk: (activity: Activity) => Promise<void> | void;
}

const ActivityEditModal: React.FC<ActivityEditModalProps> = ({
  visible,
  activity,
  date,
  startDate,
  endDate,
  onCancel,
  onOk,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');
  const [selectedFacilities, setSelectedFacilities] = useState<string[]>([]);

  // 初始化表单
  useEffect(() => {
    if (visible) {
      if (activity) {
        // 解析现有的 start_time 获取日期和时间
        let activityDate = date || startDate;
        let startTime = undefined;
        let endTime = undefined;

        if (activity.start_time) {
          const startDateTime = dayjs(activity.start_time);
          activityDate = startDateTime.format('YYYY-MM-DD');
          startTime = startDateTime;
        }
        if (activity.end_time) {
          endTime = dayjs(activity.end_time);
        }

        form.setFieldsValue({
          title: activity.title,
          description: activity.description,
          item_type: activity.item_type || 'attraction',
          location: activity.location,
          address: activity.address,
          date: activityDate ? dayjs(activityDate) : undefined,
          start_time: startTime,
          end_time: endTime,
          phone: activity.phone,
          website: activity.website,
          priority: activity.priority || 'optional',
        });

        // 设置开放时间
        if (activity.opening_hours) {
          form.setFieldsValue({
            weekday_open: activity.opening_hours.weekday,
            weekend_open: activity.opening_hours.weekend,
          });
        }

        // 设置服务设施
        if (activity.facilities) {
          setSelectedFacilities(activity.facilities);
        }
      } else {
        form.resetFields();
        form.setFieldsValue({
          item_type: 'attraction',
          date: date ? dayjs(date) : (startDate ? dayjs(startDate) : undefined),
          priority: 'optional',
        });
        setSelectedFacilities([]);
      }
      setActiveTab('basic');
    }
  }, [visible, activity, form, date, startDate]);

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // 合并日期和时间
      let start_time = undefined;
      let end_time = undefined;

      if (values.date) {
        const dateStr = values.date.format('YYYY-MM-DD');
        if (values.start_time) {
          start_time = `${dateStr}T${values.start_time.format('HH:mm')}:00`;
        } else {
          start_time = `${dateStr}T00:00:00`;
        }
        if (values.end_time) {
          end_time = `${dateStr}T${values.end_time.format('HH:mm')}:00`;
        }
      }

      // 构建开放时间对象
      const opening_hours = {
        weekday: values.weekday_open,
        weekend: values.weekend_open,
      };

      const activityData: Activity = {
        id: activity?.id,
        title: values.title,
        description: values.description,
        item_type: values.item_type,
        location: values.location,
        address: values.address,
        start_time,
        end_time,
        phone: values.phone,
        website: values.website,
        facilities: selectedFacilities,
        priority: values.priority,
        opening_hours: opening_hours.weekday || opening_hours.weekend ? opening_hours : undefined,
      };

      await onOk(activityData);
      message.success(activity ? '活动已更新' : '活动已添加');
      onCancel();
    } catch (error: any) {
      if (error.errorFields) {
        return; // 表单验证错误
      }
      message.error('操作失败：' + (error.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  // 禁用不在行程日期范围内的日期
  const disabledDate = (current: dayjs.Dayjs) => {
    if (!current) return false;
    const start = startDate ? dayjs(startDate).startOf('day') : null;
    const end = endDate ? dayjs(endDate).endOf('day') : null;
    if (start && current < start) return true;
    if (end && current > end) return true;
    return false;
  };

  // 处理地点选择
  const handleLocationSelect = (location: any) => {
    form.setFieldsValue({
      location: location.name,
      address: location.address,
      phone: location.tel,
    });
    // 可以存储坐标信息
    if (location.location) {
      // coordinates 可以在 details 中存储
      const currentDetails = form.getFieldValue('details') || {};
      form.setFieldsValue({
        details: {
          ...currentDetails,
          coordinates: location.location,
        },
      });
    }
  };

  // 切换设施选择
  const toggleFacility = (facility: string) => {
    setSelectedFacilities(prev =>
      prev.includes(facility)
        ? prev.filter(f => f !== facility)
        : [...prev, facility]
    );
  };

  return (
    <Modal
      title={activity ? '编辑活动' : '添加活动'}
      open={visible}
      onCancel={onCancel}
      onOk={handleSubmit}
      confirmLoading={loading}
      width={700}
      destroyOnClose
      className="activity-edit-modal"
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'basic',
            label: '基本信息',
            children: (
              <Form
                form={form}
                layout="vertical"
                initialValues={{ item_type: 'attraction', priority: 'optional' }}
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="title"
                      label="活动名称"
                      rules={[{ required: true, message: '请输入活动名称' }]}
                    >
                      <Input placeholder="请输入活动名称" maxLength={100} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="item_type"
                      label="活动类型"
                      rules={[{ required: true, message: '请选择活动类型' }]}
                    >
                      <Select placeholder="请选择活动类型">
                        {ACTIVITY_TYPES.map(type => (
                          <Option key={type.value} value={type.value}>{type.label}</Option>
                        ))}
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item name="description" label="活动描述">
                  <TextArea
                    placeholder="请输入活动描述"
                    rows={3}
                    maxLength={500}
                    showCount
                  />
                </Form.Item>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="location" label="地点名称">
                      <Input placeholder="请输入地点名称" prefix={<EnvironmentOutlined />} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="address" label="详细地址">
                      <Input placeholder="请输入详细地址" />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="date"
                      label="活动日期"
                      rules={[{ required: true, message: '请选择活动日期' }]}
                    >
                      <DatePicker
                        style={{ width: '100%' }}
                        placeholder="请选择活动日期"
                        prefix={<CalendarOutlined />}
                        disabledDate={disabledDate}
                        format="YYYY-MM-DD"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="活动时间（可选）">
                      <Input.Group compact>
                        <Form.Item name="start_time" noStyle>
                          <TimePicker
                            format="HH:mm"
                            placeholder="开始时间"
                            style={{ width: '45%' }}
                          />
                        </Form.Item>
                        <span style={{ display: 'inline-block', width: '10%', textAlign: 'center', lineHeight: '32px' }}>-</span>
                        <Form.Item name="end_time" noStyle>
                          <TimePicker
                            format="HH:mm"
                            placeholder="结束时间"
                            style={{ width: '45%' }}
                          />
                        </Form.Item>
                      </Input.Group>
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item name="priority" label="优先级">
                  <Select placeholder="请选择优先级">
                    {PRIORITY_OPTIONS.map(opt => (
                      <Option key={opt.value} value={opt.value}>
                        <Tag color={opt.color}>{opt.label}</Tag>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Form>
            ),
          },
          {
            key: 'details',
            label: '详细信息',
            children: (
              <Form form={form} layout="vertical">
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="phone" label="联系电话">
                      <Input placeholder="请输入联系电话" prefix={<PhoneOutlined />} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="website" label="网址">
                      <Input placeholder="请输入网址" prefix={<GlobalOutlined />} />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item label="开放时间">
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item name="weekday_open" noStyle>
                        <Input placeholder="工作日时间，如 09:00-18:00" prefix={<ClockCircleOutlined />} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name="weekend_open" noStyle>
                        <Input placeholder="周末时间，如 10:00-20:00" prefix={<ClockCircleOutlined />} />
                      </Form.Item>
                    </Col>
                  </Row>
                </Form.Item>

                <Form.Item label="服务设施">
                  <div className="facilities-tags">
                    {FACILITY_OPTIONS.map(facility => (
                      <Tag
                        key={facility}
                        color={selectedFacilities.includes(facility) ? 'blue' : 'default'}
                        style={{ cursor: 'pointer', marginBottom: 8 }}
                        onClick={() => toggleFacility(facility)}
                      >
                        {facility}
                      </Tag>
                    ))}
                  </div>
                </Form.Item>
              </Form>
            ),
          },
          {
            key: 'search',
            label: '地点搜索',
            children: (
              <div style={{ maxHeight: 400, overflow: 'auto' }}>
                <LocationSearch
                  onSelect={handleLocationSelect}
                  showFavorites={true}
                />
              </div>
            ),
          },
        ]}
      />
    </Modal>
  );
};

export default ActivityEditModal;
