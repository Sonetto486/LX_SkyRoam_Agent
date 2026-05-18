import React, { useState } from 'react';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import './AttractionImageCarousel.css';

interface AttractionImageCarouselProps {
  images?: (string | null)[];  // 图片URL数组，可包含null
  attractionName?: string;       // 景点名称（用于alt文本）
  maxImagesToShow?: number;      // 最多显示的图片数量（默认2张）
}

const AttractionImageCarousel: React.FC<AttractionImageCarouselProps> = ({
  images = [],
  attractionName = '景点',
  maxImagesToShow = 2
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loadingStates, setLoadingStates] = useState<boolean[]>([]);

  // 过滤并限制有效的图片
  // 修复后的代码
const validImages: string[] = images
  .filter((img): img is string => img !== null && img !== undefined && (img as string).trim().length > 0)
  .slice(0, maxImagesToShow);

  // 初始化加载状态
  React.useEffect(() => {
    setLoadingStates(new Array(validImages.length).fill(true));
  }, [validImages.length]);

  // 如果没有有效图片，不显示轮播
  if (validImages.length === 0) {
    return (
      <div className="attraction-image-carousel-empty">
        <div className="placeholder-image">📷 暂无图片</div>
      </div>
    );
  }

  const handlePrev = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev === 0 ? validImages.length - 1 : prev - 1));
  };

  const handleNext = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev === validImages.length - 1 ? 0 : prev + 1));
  };

  const handleImageLoad = (index: number) => {
    setLoadingStates((prev) => {
      const newStates = [...prev];
      newStates[index] = false;
      return newStates;
    });
  };

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement>, index: number) => {
    // 图片加载失败时显示占位符
    (e.target as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="300" height="200"%3E%3Crect fill="%23f0f0f0" width="300" height="200"/%3E%3Ctext x="50%25" y="50%25" font-family="Arial" font-size="16" fill="%23999" text-anchor="middle" dominant-baseline="middle"%3E图片加载失败%3C/text%3E%3C/svg%3E';
    setLoadingStates((prev) => {
      const newStates = [...prev];
      newStates[index] = false;
      return newStates;
    });
  };

  // 获取Wikimedia图片的缩略图URL（更快加载）
  const getOptimizedImageUrl = (url: string): string => {
    if (url.includes('wikimedia.org')) {
      // Wikimedia支持缩略图参数，添加 ?width=400 获取更小的图片
      const separator = url.includes('?') ? '&' : '?';
      return `${url}${separator}width=400`;
    }
    return url;
  };

  return (
    <div className="attraction-image-carousel">
      {/* 图片容器 */}
      <div className="carousel-image-container">
        {validImages.length > 1 && (
          <button className="carousel-nav-btn carousel-prev" onClick={handlePrev}>
            <LeftOutlined />
          </button>
        )}

        {/* 加载中占位符 */}
        {loadingStates[currentIndex] && (
          <div className="carousel-loading-placeholder">
            <div className="loading-spinner"></div>
            <span>加载中...</span>
          </div>
        )}

        <img
          src={getOptimizedImageUrl(validImages[currentIndex])}
          alt={`${attractionName} - 图片 ${currentIndex + 1}`}
          className="carousel-image"
          style={{ opacity: loadingStates[currentIndex] ? 0 : 1 }}
          onLoad={() => handleImageLoad(currentIndex)}
          onError={(e) => handleImageError(e, currentIndex)}
          loading="lazy"
        />

        {validImages.length > 1 && (
          <button className="carousel-nav-btn carousel-next" onClick={handleNext}>
            <RightOutlined />
          </button>
        )}
      </div>

      {/* 指示点 */}
      {validImages.length > 1 && (
        <div className="carousel-indicators">
          {validImages.map((_, index) => (
            <div
              key={index}
              className={`indicator-dot ${index === currentIndex ? 'active' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                setCurrentIndex(index);
              }}
            />
          ))}
        </div>
      )}

      {/* 计数器 */}
      {validImages.length > 1 && (
        <div className="carousel-counter">
          {currentIndex + 1} / {validImages.length}
        </div>
      )}
    </div>
  );
};

export default AttractionImageCarousel;
