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
  
  const totalDuration = props.slides.reduce((acc, s) => acc + s.durationInFrames, 0);
  const durationInFrames = totalDuration > 0 ? totalDuration : 30;

  return (
    <>
      <Composition
        id="MainComp"
        component={MainComp}
        durationInFrames={durationInFrames}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={props}
      />
    </>
  );
};
