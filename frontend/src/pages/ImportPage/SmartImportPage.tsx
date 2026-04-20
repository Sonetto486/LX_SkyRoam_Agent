import React, { useState } from 'react';
import { Card, Button, Upload, Input, Typography } from 'antd';
import { UploadOutlined, LinkOutlined } from '@ant-design/icons';
import './SmartImportPage.css';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

const SmartImportPage: React.FC = () => {
  const [textInput, setTextInput] = useState('');
  const [linkInput, setLinkInput] = useState('');
  const [fileList, setFileList] = useState<any[]>([]);

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setTextInput(e.target.value);
  };

  const handleLinkChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLinkInput(e.target.value);
  };

  const handleFileChange = (info: any) => {
    setFileList(info.fileList);
  };

  const handleSubmit = () => {
    // 处理导入逻辑
    console.log('Importing data:', { textInput, linkInput, fileList });
  };

  return (
    <div className="smart-import-page">
      <Title level={2}>智能导入</Title>
      <Paragraph>通过文本、链接或截图导入旅行计划</Paragraph>

      <div className="import-methods">
        {/* 文本输入 */}
        <Card title="文本输入" className="import-card">
          <TextArea
            placeholder="粘贴旅行计划文本或描述"
            value={textInput}
            onChange={handleTextChange}
            rows={6}
          />
        </Card>

        {/* 链接输入 */}
        <Card title="链接输入" className="import-card">
          <Input
            placeholder="输入旅行计划链接"
            prefix={<LinkOutlined />}
            value={linkInput}
            onChange={handleLinkChange}
          />
        </Card>

        {/* 图片上传 */}
        <Card title="截图上传" className="import-card">
          <Upload
            name="files"
            multiple
            fileList={fileList}
            onChange={handleFileChange}
            maxCount={5}
          >
            <Button icon={<UploadOutlined />}>选择文件</Button>
          </Upload>
          <Paragraph style={{ marginTop: 16 }}>支持拖拽上传截图</Paragraph>
        </Card>
      </div>

      <div className="submit-section">
        <Button type="primary" size="large" onClick={handleSubmit}>
          开始智能导入
        </Button>
      </div>
    </div>
  );
};

export default SmartImportPage;
