import React from 'react';
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig, spring, Audio, staticFile } from 'remotion';
import { MainCompProps, SlideData } from './Root';
import { Highlight, themes } from 'prism-react-renderer';

const getBackgroundGradient = (theme?: string) => {
  switch (theme) {
    case 'tech': return 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)';
    case 'warning': return 'linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%)';
    case 'success': return 'linear-gradient(135deg, #064e3b 0%, #14532d 100%)';
    case 'creative': return 'linear-gradient(135deg, #4c1d95 0%, #be185d 100%)';
    case 'dark': return 'linear-gradient(135deg, #09090b 0%, #18181b 100%)';
    case 'neon': return 'linear-gradient(135deg, #000000 0%, #065f46 100%)';
    case 'nature': return 'linear-gradient(135deg, #14532d 0%, #064e3b 100%)';
    case 'academic': return 'linear-gradient(135deg, #1e3a8a 0%, #172554 100%)';
    default: return 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)';
  }
};

export const MainComp: React.FC<MainCompProps> = ({ slides }) => {
  let accumulatedFrames = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {slides.map((slide, i) => {
        const startFrame = accumulatedFrames;
        const duration = slide.durationInFrames;
        accumulatedFrames += duration;

        return (
          <Sequence key={i} from={startFrame} durationInFrames={duration}>
            <Slide slide={slide} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const Slide: React.FC<{ slide: SlideData }> = ({ slide }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // A sleek enter animation
  const opacity = spring({
    frame,
    fps,
    config: { damping: 200 },
    durationInFrames: 30,
  });

  const translateY = spring({
    frame,
    fps,
    from: 50,
    to: 0,
    config: { damping: 15 },
    durationInFrames: 30,
  });

  // Calculate typing effect (approx 3 frames per character)
  const charsToShow = Math.floor(frame / 2);
  const textToShow = slide.text.slice(0, Math.max(0, charsToShow));
  
  const hasCode = !!slide.codeSnippet;

  return (
    <AbsoluteFill style={{ 
      justifyContent: 'center', 
      alignItems: 'center', 
      padding: '80px',
      background: getBackgroundGradient(slide.theme),
      flexDirection: 'row',
      gap: '60px'
    }}>
      {/* Play the audio if available */}
      {slide.audioPath && <Audio src={staticFile(slide.audioPath)} />}
      
      {/* Text Window */}
      <div
        style={{
          opacity,
          transform: `translateY(${translateY}px)`,
          backgroundColor: 'rgba(30, 41, 59, 0.8)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '24px',
          padding: '60px',
          flex: hasCode ? 1 : 'none',
          width: hasCode ? 'auto' : '100%',
          maxWidth: hasCode ? 'auto' : '1400px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          backdropFilter: 'blur(10px)'
        }}
      >
        <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
          <div style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#ef4444' }} />
          <div style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#eab308' }} />
          <div style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#22c55e' }} />
        </div>
        <div style={{
          fontFamily: 'monospace',
          fontSize: '48px',
          lineHeight: '1.5',
          color: '#e2e8f0',
          fontWeight: '500',
        }}>
          {textToShow}
          <span style={{ 
            display: 'inline-block', 
            width: '24px', 
            height: '48px', 
            backgroundColor: '#38bdf8',
            marginLeft: '8px',
            verticalAlign: 'bottom',
            opacity: frame % 20 < 10 ? 1 : 0
          }} />
        </div>
      </div>

      {/* Code Window */}
      {hasCode && (
        <div
          style={{
            opacity,
            transform: `translateY(${translateY + 20}px)`,
            backgroundColor: '#0d1117',
            border: '1px solid #30363d',
            borderRadius: '16px',
            padding: '40px',
            flex: 1,
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}
        >
          <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', opacity: 0.5 }}>
            <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#8b949e' }} />
            <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#8b949e' }} />
            <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#8b949e' }} />
          </div>
          <Highlight
            theme={themes.vsDark}
            code={slide.codeSnippet || ''}
            language={slide.codeLanguage || 'javascript'}
          >
            {({ className, style, tokens, getLineProps, getTokenProps }) => (
              <pre className={className} style={{ ...style, fontSize: '32px', fontFamily: 'monospace', background: 'transparent' }}>
                {tokens.map((line, i) => (
                  <div key={i} {...getLineProps({ line })}>
                    {line.map((token, key) => (
                      <span key={key} {...getTokenProps({ token })} />
                    ))}
                  </div>
                ))}
              </pre>
            )}
          </Highlight>
        </div>
      )}
    </AbsoluteFill>
  );
};
