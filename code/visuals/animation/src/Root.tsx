import {Composition, Still} from 'remotion';
import {Figure, NeuronFilm} from './Composition';
import {figureHeights} from './neuron.mjs';
import {CourseFigure, CourseProcess} from './Course';

export const RemotionRoot: React.FC = () => <>
  <Composition id="NeuronFlow" component={NeuronFilm} durationInFrames={420}
    fps={30} width={1080} height={1500}/>
  <Still id="NeuronFigure" component={Figure} width={1080} height={1040}
    defaultProps={{figure: 'roles'}}
    calculateMetadata={({props}) => ({height: figureHeights[props.figure as keyof typeof figureHeights] ?? 1040})}/>
  <Still id="CourseFigure" component={CourseFigure} width={1080} height={1500}
    defaultProps={{markup: '', phases: [0], height: 1500}}
    calculateMetadata={({props}) => ({height: props.height})}/>
  <Composition id="CourseProcess" component={CourseProcess} width={1080} height={1500}
    durationInFrames={300} fps={30}
    defaultProps={{markup: '', phases: [0, 1, 2, 3], height: 1500, frames: [] as {markup: string; phase: number}[]}}
    calculateMetadata={({props}) => ({height: props.height,
      durationInFrames: Math.max(120, ((props.frames?.length ?? props.phases.length) + 1) * 60)})}/>
</>;
