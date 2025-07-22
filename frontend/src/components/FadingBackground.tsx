import React, { useState, useEffect } from 'react';

interface FadingBackgroundProps {
  blur?: boolean;
}

const bgImages = [
  process.env.PUBLIC_URL + '/backgrounds/image_1.png',
  process.env.PUBLIC_URL + '/backgrounds/image_2.png',
  process.env.PUBLIC_URL + '/backgrounds/image_3.jpeg',
  process.env.PUBLIC_URL + '/backgrounds/image_4.jpeg',
  process.env.PUBLIC_URL + '/backgrounds/image_5.jpeg',
];

const FadingBackground: React.FC<FadingBackgroundProps> = ({ blur = true }) => {
  const [bgIndex, setBgIndex] = useState(0);
  const [fade, setFade] = useState(false);
  useEffect(() => {
    const interval = setInterval(() => {
      setBgIndex(i => (i + 1) % bgImages.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);
  useEffect(() => {
    setFade(true);
    const timeout = setTimeout(() => setFade(false), 1000);
    return () => clearTimeout(timeout);
  }, [bgIndex]);

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: -1, pointerEvents: 'none', overflow: 'hidden' }}>
      {bgImages.map((img, i) => (
        <img
          key={img}
          src={img}
          alt="bg"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            objectFit: 'cover',
            opacity: i === bgIndex ? (fade ? 0.7 : 1) : 0,
            transition: 'opacity 1.2s',
            filter: blur ? 'blur(16px) brightness(0.5)' : 'none',
          }}
        />
      ))}
    </div>
  );
};

export default FadingBackground; 