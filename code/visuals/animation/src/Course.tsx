import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {headSplitFrame, ropeFrame} from './mechanisms.mjs';

type SceneFrame = {markup: string; phase: number};
export type CourseProps = {markup: string; phases: number[]; height: number; number?: number; frames?: SceneFrame[]};
export const CourseFigure: React.FC<CourseProps> = ({markup}) => (
  <AbsoluteFill dangerouslySetInnerHTML={{__html: markup}} />
);
export const CourseProcess: React.FC<CourseProps> = ({markup, phases, frames, number}) => {
  const frame = useCurrentFrame();
  if (number === 12 || number === 13) {
    const moving = number === 12 ? headSplitFrame(frame) : ropeFrame(frame);
    return <AbsoluteFill dangerouslySetInnerHTML={{__html: moving}} />;
  }
  const count = frames?.length ?? phases.length;
  const index = Math.min(count - 1, Math.floor(frame / 60));
  const current = frames?.[index] ?? {markup, phase: phases[index]};
  const progress = Math.min(1, (frame - index * 60) / 14);
  const selectors = [...current.markup.matchAll(/data-phase="(\d+)"/g)].map(match => Number(match[1]));
  const style = [...new Set(selectors)].map(phase => {
    const opacity = phase < current.phase ? 1 : phase === current.phase ? .12 + progress * .88 : .12;
    return `[data-phase="${phase}"]{opacity:${opacity}}`;
  }).join('');
  const styled = current.markup.replace('</defs>', `</defs><style>${style}</style>`);
  return <AbsoluteFill dangerouslySetInnerHTML={{__html: styled}} />;
};
