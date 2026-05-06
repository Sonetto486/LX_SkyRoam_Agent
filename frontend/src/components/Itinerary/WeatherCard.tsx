import React, { useState, useEffect } from 'react';
import { Spin, Empty, Card, Tooltip } from 'antd';
import { CloudOutlined, SunOutlined, CloudFilled, ThunderboltOutlined, CloudSyncOutlined, InfoCircleOutlined, CalendarOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { buildApiUrl } from '../../config/api';
import './WeatherCard.css';

interface WeatherData {
  date: string;
  dayWeather: string;
  nightWeather: string;
  dayTemp: string;
  nightTemp: string;
  windDirection: string;
  windPower: string;
}

interface WeatherCardProps {
  city: string;
  startDate: string;
  days?: number;
}

// 天气图标映射
const getWeatherIcon = (weather: string) => {
  const weatherLower = weather.toLowerCase();
  if (weatherLower.includes('晴')) return <SunOutlined style={{ color: '#faad14', fontSize: 24 }} />;
  if (weatherLower.includes('云') || weatherLower.includes('阴')) return <CloudFilled style={{ color: '#8c8c8c', fontSize: 24 }} />;
  if (weatherLower.includes('雨')) return <CloudSyncOutlined style={{ color: '#1890ff', fontSize: 24 }} />;
  if (weatherLower.includes('雷')) return <ThunderboltOutlined style={{ color: '#722ed1', fontSize: 24 }} />;
  return <CloudOutlined style={{ color: '#8c8c8c', fontSize: 24 }} />;
};

const WeatherCard: React.FC<WeatherCardProps> = ({ city, startDate, days = 7 }) => {
  const [loading, setLoading] = useState(true);
  const [weatherData, setWeatherData] = useState<WeatherData[]>([]);
  const [dateMode, setDateMode] = useState<'travel_date' | 'current'>('current');
  const [dateReason, setDateReason] = useState<string>('');

  useEffect(() => {
    const fetchWeather = async () => {
      if (!city) {
        setLoading(false);
        return;
      }

      setLoading(true);

      // 确保至少显示7天天气
      const minDays = Math.max(7, days);

      try {
        // 调用后端天气API，传递旅行日期
        const res = await fetch(buildApiUrl(`/weather?city=${encodeURIComponent(city)}&days=${minDays}&travel_date=${encodeURIComponent(startDate)}`));

        if (!res.ok) {
          throw new Error('获取天气失败');
        }

        const data = await res.json();

        // 保存日期模式信息
        if (data.date_mode) {
          setDateMode(data.date_mode);
        }
        if (data.date_reason) {
          setDateReason(data.date_reason);
        }

        if (data.forecast && data.forecast.length > 0) {
          setWeatherData(data.forecast.map((cast: any) => ({
            date: cast.date,
            dayWeather: cast.dayweather,
            nightWeather: cast.nightweather,
            dayTemp: cast.daytemp,
            nightTemp: cast.nighttemp,
            windDirection: cast.daywind,
            windPower: cast.daypower,
          })));
        } else {
          // 无数据时使用模拟数据
          setWeatherData(generateMockWeather(startDate, minDays));
        }
      } catch (err: any) {
        console.warn('天气API调用失败，使用模拟数据:', err);
        // 失败时使用模拟数据
        setWeatherData(generateMockWeather(startDate, minDays));
      } finally {
        setLoading(false);
      }
    };

    fetchWeather();
  }, [city, startDate, days]);

  // 生成模拟天气数据（从startDate开始）
  const generateMockWeather = (start: string, count: number): WeatherData[] => {
    const result: WeatherData[] = [];
    const weathers = ['晴', '多云', '阴', '小雨', '中雨'];
    const startDateObj = new Date(start);

    for (let i = 0; i < count; i++) {
      const date = new Date(startDateObj);
      date.setDate(date.getDate() + i);
      const weatherIndex = Math.floor(Math.random() * weathers.length);
      const baseTemp = 20 + Math.floor(Math.random() * 10);

      result.push({
        date: date.toISOString().split('T')[0],
        dayWeather: weathers[weatherIndex],
        nightWeather: weathers[Math.max(0, weatherIndex - 1)],
        dayTemp: String(baseTemp),
        nightTemp: String(baseTemp - 5),
        windDirection: '东南',
        windPower: '3',
      });
    }

    return result;
  };

  // 格式化日期显示
  const formatDateDisplay = (dateStr: string) => {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };

  // 获取标题
  const getTitle = () => {
    const modeIcon = dateMode === 'travel_date'
      ? <CalendarOutlined style={{ color: '#52c41a' }} />
      : <ClockCircleOutlined style={{ color: '#1890ff' }} />;

    return (
      <span>
        天气预报（{weatherData.length}天）
        <Tooltip title={dateReason || '点击查看详情'}>
          <span style={{ marginLeft: 8, cursor: 'pointer' }}>
            {modeIcon}
          </span>
        </Tooltip>
      </span>
    );
  };

  if (loading) {
    return (
      <Card className="weather-card-container" title="天气预报">
        <div className="weather-loading">
          <Spin />
        </div>
      </Card>
    );
  }

  if (weatherData.length === 0) {
    return (
      <Card className="weather-card-container" title="天气预报">
        <Empty description="暂无天气数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    );
  }

  return (
    <Card className="weather-card-container" title={getTitle()}>
      {/* 显示日期模式提示 */}
      {dateReason && (
        <div className="weather-mode-hint" style={{
          marginBottom: 8,
          fontSize: 12,
          color: '#8c8c8c',
          display: 'flex',
          alignItems: 'center',
          gap: 4
        }}>
          {dateMode === 'travel_date' ? (
            <>
              <CalendarOutlined />
              <span>显示行程期间天气</span>
            </>
          ) : (
            <>
              <ClockCircleOutlined />
              <span>显示近期天气（{dateReason}）</span>
            </>
          )}
        </div>
      )}
      <div className="weather-cards">
        {weatherData.map((weather, index) => (
          <div key={index} className="weather-item">
            <div className="weather-date">{formatDateDisplay(weather.date)}</div>
            <div className="weather-icon">{getWeatherIcon(weather.dayWeather)}</div>
            <div className="weather-temp">
              {weather.dayTemp}°/{weather.nightTemp}°
            </div>
            <div className="weather-condition">{weather.dayWeather}</div>
          </div>
        ))}
      </div>
    </Card>
  );
};

export default WeatherCard;
