import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {svg} from './neuron.mjs';
import example from './lesson01.json';

export type FigureProps = {figure: string};
export const SvgDocument: React.FC<{markup: string}> = ({markup}) => (
  <AbsoluteFill dangerouslySetInnerHTML={{__html: markup}} />
);
export const Figure: React.FC<FigureProps> = ({figure}) => (
  <AbsoluteFill dangerouslySetInnerHTML={{__html: svg(figure, example)}} />
);

export const NeuronFilm: React.FC = () => {
  const frame = useCurrentFrame();
  const step = Math.min(5, Math.floor(frame / 70));
  const progress = Math.min(1, (frame % 70) / 45);
  return <AbsoluteFill dangerouslySetInnerHTML={{__html: svg('flow', example, step, progress)}} />;
};
