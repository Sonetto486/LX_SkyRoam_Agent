import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, DatePicker, InputNumber, TimePicker, message } from 'antd';
import { EnvironmentOutlined, ClockCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
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

interface Activity {
  id?: number;
  title: string;
  description?: string;
  item_type: string;
  start_time?: string;
  end_time?: string;
  duration_hours?: number;
  location?: string;
  address?: string;
  coordinates?: { lat: number; lng: number };
  details?: any;
  images?: string[];
}

interface ActivityEditModalProps {
  visible: boolean;
  activity?: Activity | null;
  date?: string;
  onCancel: () => void;
  onOk: (activity: Activity) => Promise<void>;
}

const ActivityEditModal: React.FC<ActivityEditModalProps> = ({
  visible,
  activity,
  date,
  onCancel,
  onOk,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  // 初始化表单
  useEffect(() => {
    if (visible) {
      if (activity) {
        form.setFieldsValue({
          title: activity.title,
          description: activity.description,
          item_type: activity.item_type || 'attraction',
          location: activity.location,
          address: activity.address,
          duration_hours: activity.duration_hours,
          start_time: activity.start_time ? dayjs(activity.start_time, 'HH:mm') : undefined,
          end_time: activity.end_time ? dayjs(activity.end_time, 'HH:mm') : undefined,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({ item_type: 'attraction' });
      }
    }
  }, [visible, activity, form]);

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const activityData: Activity = {
        id: activity?.id,
        title: values.title,
        description: values.description,
        item_type: values.item_type,
        location: values.location,
        address: values.address,
        duration_hours: values.duration_hours,
        start_time: values.start_time ? values.start_time.format('HH:mm') : undefined,
        end_time: values.end_time ? values.end_time.format('HH:mm') : undefined,
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

  return (
    <Modal
      title={activity ? '编辑活动' : '添加活动'}
      open={visible}
      onCancel={onCancel}
      onOk={handleSubmit}
      confirmLoading={loading}
      width={600}
      destroyOnClose
      className="activity-edit-modal"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{ item_type: 'attraction' }}
      >
        <Form.Item
          name="title"
          label="活动名称"
          rules={[{ required: true, message: '请输入活动名称' }]}
        >
          <Input placeholder="请输入活动名称" maxLength={100} />
        </Form.Item>

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

        <Form.Item name="description" label="活动描述">
          <TextArea
            placeholder="请输入活动描述"
            rows={3}
            maxLength={500}
            showCount
          />
        </Form.Item>

        <Form.Item name="location" label="地点名称">
          <Input placeholder="请输入地点名称" prefix={<EnvironmentOutlined />} />
        </Form.Item>

        <Form.Item name="address" label="详细地址">
          <Input placeholder="请输入详细地址" />
        </Form.Item>

        <Form.Item label="活动时间">
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

        <Form.Item name="duration_hours" label="预计时长（小时）">
          <InputNumber
            min={0.5}
            max={24}
            step={0.5}
            placeholder="预计时长"
            style={{ width: '100%' }}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ActivityEditModal;
