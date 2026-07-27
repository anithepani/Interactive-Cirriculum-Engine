import { Composition, getInputProps } from 'remotion';
import { MainComp } from './Composition';

export type SlideData = {
  text: string;
  durationInFrames: number;
  audioPath: string;
  theme?: string;
  codeSnippet?: string;
  codeLanguage?: string;
};

export type MainCompProps = {
  slides: SlideData[];
  width?: number;
  height?: number;
};

export const Root: React.FC = () => {
  // get input props provided via --props
  const defaultProps: MainCompProps = {
    slides: [
      {
        text: 'Welcome to the curriculum engine.',
        durationInFrames: 90,
        audioPath: '',
      }
    ]
  };

  const inputProps = getInputProps() as MainCompProps;
  const props = inputProps.slides ? inputProps : defaultProps;

  // Resolution is settings-driven: the worker passes width/height via --props
  // (default 1280x720 — half the pixel work of 1080p, ample for a summary).
  const width = props.width ?? 1280;
  const height = props.height ?? 720;

  const totalDuration = props.slides.reduce((acc, s) => acc + s.durationInFrames, 0);
  const durationInFrames = totalDuration > 0 ? totalDuration : 30;

  return (
    <>
      <Composition
        id="MainComp"
        component={MainComp}
        durationInFrames={durationInFrames}
        fps={30}
        width={width}
        height={height}
        defaultProps={props}
      />
    </>
  );
};
