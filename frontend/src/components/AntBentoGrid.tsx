import React from 'react';
import { Row, Col, Card } from 'antd';
import type { CardProps } from 'antd';

// Define tile size types
export type TileSize = 'small' | 'medium' | 'large' | 'xlarge';

// Define responsive breakpoints
export interface TileConfig {
  size: TileSize;
  content: React.ReactNode;
  key: string;
  title?: string;
  cardProps?: CardProps;
}

// Map tile sizes to column spans for different breakpoints
const sizeToSpan = {
  small: { xs: 24, sm: 12, md: 8, lg: 6, xl: 6, xxl: 6 },
  medium: { xs: 24, sm: 24, md: 12, lg: 12, xl: 12, xxl: 12 },
  large: { xs: 24, sm: 24, md: 16, lg: 18, xl: 18, xxl: 18 },
  xlarge: { xs: 24, sm: 24, md: 24, lg: 24, xl: 24, xxl: 24 },
};

export interface AntBentoGridProps {
  tiles: TileConfig[];
  gutter?: [number, number];
  className?: string;
  style?: React.CSSProperties;
}

const AntBentoGrid: React.FC<AntBentoGridProps> = ({
  tiles,
  gutter = [16, 16],
  className = '',
  style = {},
}) => {
  return (
    <Row 
      gutter={gutter} 
      className={`ant-bento-grid ${className}`}
      style={{
        ...style,
        width: '100%',
      }}
    >
      {tiles.map((tile) => {
        const spans = sizeToSpan[tile.size];
        
        return (
          <Col
            key={tile.key}
            xs={spans.xs}
            sm={spans.sm}
            md={spans.md}
            lg={spans.lg}
            xl={spans.xl}
            xxl={spans.xxl}
          >
            <Card
              title={tile.title}
              bordered={false}
              style={{
                height: '100%',
                background: '#111113',
                border: '1px solid #2a2a30',
                borderRadius: 12,
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                overflow: 'hidden',
              }}
              hoverable
              {...tile.cardProps}
              className={`bento-tile bento-tile-${tile.size} ${tile.cardProps?.className || ''}`}
            >
              {tile.content}
            </Card>
          </Col>
        );
      })}
    </Row>
  );
};

// Style helper for consistent tile heights
export const tileHeights = {
  small: { minHeight: 200, height: 'auto' },
  medium: { minHeight: 300, height: 'auto' },
  large: { minHeight: 400, height: 'auto' },
  xlarge: { minHeight: 500, height: 'auto' },
};

// Helper function to create tile configurations
export const createTile = (
  key: string,
  size: TileSize,
  title: string,
  content: React.ReactNode,
  cardProps?: CardProps
): TileConfig => ({
  key,
  size,
  title,
  content,
  cardProps: {
    ...cardProps,
    style: {
      ...tileHeights[size],
      ...cardProps?.style,
    },
  },
});

export default AntBentoGrid;