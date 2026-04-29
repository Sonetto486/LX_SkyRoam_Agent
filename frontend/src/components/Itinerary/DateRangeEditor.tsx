import React, { useState, useEffect } from 'react';
import { Modal, Form, DatePicker, InputNumber, message, Space, Button } from 'antd';
import { CalendarOutlined } from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import './DateRangeEditor.css';

const { RangePicker } = DatePicker;

interface DateRangeEditorProps {
  visible: boolean;
  title?: string;
  startDate?: string;
  endDate?: string;
  durationDays?: number;
  onCancel: () => void;
  onOk: (startDate: string, endDate: string, durationDays: number) => Promise<void>;
}

const DateRangeEditor: React.FC<DateRangeEditorProps> = ({
  visible,
  title = '修改行程日期',
  startDate,
  endDate,
  durationDays,
  onCancel,
  onOk,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null]>([null, null]);

  // 初始化表单
  useEffect(() => {
    if (visible && startDate && endDate) {
      const start = dayjs(startDate);
      const end = dayjs(endDate);
      setDateRange([start, end]);
      form.setFieldsValue({
        dateRange: [start, end],
        durationDays: end.diff(start, 'day') + 1,
      });
    }
  }, [visible, startDate, endDate, form]);

  // 计算天数
  const calculateDays = (start: Dayjs | null, end: Dayjs | null): number => {
    if (!start || !end) return 1;
    return end.diff(start, 'day') + 1;
  };

  // 日期范围变化
  const handleDateChange = (dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setDateRange(dates);
      const days = calculateDays(dates[0], dates[1]);
      form.setFieldsValue({ durationDays: days });
    }
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const start = values.dateRange[0].format('YYYY-MM-DD');
      const end = values.dateRange[1].format('YYYY-MM-DD');
      const days = values.durationDays;

      await onOk(start, end, days);
      message.success('日期已更新');
      onCancel();
    } catch (error: any) {
      if (error.errorFields) {
        return;
      }
      message.error('更新失败：' + (error.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={title}
      open={visible}
      onCancel={onCancel}
      onOk={handleSubmit}
      confirmLoading={loading}
      destroyOnClose
      className="date-range-editor"
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          确定
        </Button>,
      ]}
    >
      <Form
        form={form}
        layout="vertical"
      >
        <Form.Item
          name="dateRange"
          label="行程日期"
          rules={[{ required: true, message: '请选择行程日期' }]}
        >
          <RangePicker
            style={{ width: '100%' }}
            format="YYYY-MM-DD"
            onChange={handleDateChange as any}
            placeholder={['开始日期', '结束日期']}
            suffixIcon={<CalendarOutlined />}
          />
        </Form.Item>

        <Form.Item
          name="durationDays"
          label="行程天数"
        >
          <InputNumber
            min={1}
            max={30}
            style={{ width: '100%' }}
            disabled
            addonAfter="天"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default DateRangeEditor;
