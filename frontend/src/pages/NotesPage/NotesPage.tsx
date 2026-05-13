import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Typography, Button, Input, Spin, Empty, Card, Tag, Space, message } from 'antd';
import { ArrowLeftOutlined, SearchOutlined, EnvironmentOutlined, StarOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import Masonry from 'react-masonry-css';
import { authFetch } from '../../utils/auth';
import './NotesPage.css';

const { Title } = Typography;

interface Note {
  id: number;
  title: string;
  destination: string;
  image_url: string;
  travel_feelings?: string;
  rating?: number;
}

const NotesPage: React.FC = () => {
  const navigate = useNavigate();
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [searchValue, setSearchValue] = useState('');
  const [total, setTotal] = useState(0);
  
  const loadingRef = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchNotes = useCallback(async (pageNum: number, keyword: string, isNewSearch: boolean = false) => {
    if (loadingRef.current) return;
    
    loadingRef.current = true;
    setLoading(true);
    
    try {
      const limit = 20;
      const url = `/notes?limit=${limit}&page=${pageNum}&keyword=${encodeURIComponent(keyword)}`;
      const response = await authFetch(url);
      const data = await response.json();
      
      const newNotes = data.items || [];
      if (isNewSearch) {
        setNotes(newNotes);
      } else {
        setNotes(prev => [...prev, ...newNotes]);
      }
      
      setTotal(data.total || 0);
      setHasMore(newNotes.length === limit);
      setPage(pageNum);
    } catch (error) {
      console.error('获取灵感失败:', error);
      message.error('获取灵感列表失败');
    } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  }, []);

  useEffect(() => {
    fetchNotes(1, '', true);
  }, [fetchNotes]);

  // 无限滚动监听
  useEffect(() => {
    const handleScroll = () => {
      if (!hasMore || loadingRef.current) return;
      
      const scrollHeight = document.documentElement.scrollHeight;
      const scrollTop = document.documentElement.scrollTop;
      const clientHeight = document.documentElement.clientHeight;
      
      if (scrollTop + clientHeight >= scrollHeight - 500) {
        fetchNotes(page + 1, searchValue);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [page, hasMore, searchValue, fetchNotes]);

  const handleSearch = (value: string) => {
    setSearchValue(value);
    setPage(1);
    fetchNotes(1, value, true);
  };

  const breakpointColumnsObj = {
    default: 4,
    1100: 3,
    700: 2,
    500: 1
  };

  return (
    <div className="notes-page">
      <div className="page-header">
        <Button 
          type="link" 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/discover')}
          className="back-btn"
        >
          返回发现页
        </Button>
        <div className="header-content">
          <Title level={2}>旅行灵感墙</Title>
          <Input.Search
            placeholder="搜索灵感、目的地..."
            allowClear
            onSearch={handleSearch}
            className="search-box"
            enterButton
          />
        </div>
      </div>

      <div className="notes-container" ref={containerRef}>
        {notes.length > 0 ? (
          <Masonry
            breakpointCols={breakpointColumnsObj}
            className="my-masonry-grid"
            columnClassName="my-masonry-grid_column"
          >
            {notes.map(note => (
              <div key={note.id} className="note-item" onClick={() => navigate(`/notes/${note.id}`)}>
                <Card
                  hoverable
                  cover={<img alt={note.title} src={note.image_url} />}
                  className="note-card"
                >
                  <Card.Meta 
                    title={note.title} 
                    description={
                      <div className="note-card-footer">
                        <Space className="note-dest">
                          <EnvironmentOutlined />
                          <span>{note.destination}</span>
                        </Space>
                        <div className="note-desc-text">
                            {note.travel_feelings}
                        </div>
                        <Button 
                          type="primary" 
                          size="small" 
                          block
                          style={{ marginTop: 12, borderRadius: 6 }}
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/notes/${note.id}`);
                          }}
                        >
                          查看详情
                        </Button>
                      </div>
                    }
                  />
                </Card>
              </div>
            ))}
          </Masonry>
        ) : !loading && (
          <Empty description="没有找到相关的旅行灵感" />
        )}
        
        {loading && (
          <div className="loading-more">
            <Spin size="large" tip="加载更多灵感..." />
          </div>
        )}
        
        {!hasMore && notes.length > 0 && (
          <div className="no-more">已加载全部灵感</div>
        )}
      </div>
    </div>
  );
};

export default NotesPage;
