export const COPY = {
  zh: {
    language: 'zh-CN', title: '把特征分开，位置一个不少',
    eyebrow: 'HELLO LLM / 第 12 讲 · 三维张量实验', back: '← 回到文章',
    lead: '跟住一个数字，看拆头、交换轴和合头怎样重排坐标。每个头都保留全部位置，12 个数始终不变。',
    shape: '当前形状', trace: '追踪数字', original: '原始索引', current: '当前索引', unchanged: '数值始终不变',
    step: '步骤', previous: '上一步', next: '下一步', replay: '重来', play: '播放', pause: '暂停',
    orbit: '自由旋转', fixed: '固定视角', reset: '恢复视角', front: '正面', angle: '斜侧', zoomIn: '放大', zoomOut: '缩小',
    scene: '带数字的三维张量，可通过下方数字按钮选择坐标',
    loading: '正在准备三维视图…', ready: '固定视角 · 逐步查看',
    orbitHelp: '拖动旋转；双指缩放。步骤与数字按钮也可操作。',
    fallback: '此设备暂时无法显示三维视图，下方索引表仍可逐步查看。',
    noScript: '启用 JavaScript 后可操作三维实验，也可查看完整静态拆分图。',
    staticLink: '查看静态拆分图', details: '索引表与说明（可滚动）', table: '点一个数，核对它的索引', value: '数字', index: '索引',
    head0: '头 0 · 前两项', head1: '头 1 · 后两项', selected: '黑框 · 当前追踪',
    scope: '本实验只拆分、交换轴与拼回，不执行投影或注意力计算。正式注意力中，Q/K/V 先投影，再分头。',
    note: '拆分后的三个空间方向对应位置、头与头内坐标；轴顺序随步骤改变，批次 B=1 固定。方块厚度用于分辨格子，不代表额外维度。',
    source: '数据来自第 12 讲保存的实验记录，未重新训练。',
    axes: [
      ['横向：特征 D', '纵向：位置 T', ''], ['横向：头内坐标 d', '纵向：位置 T', '纵深：头 H'],
      ['横向：头内坐标 d', '纵向：头 H', '纵深：位置 T'], ['横向：头内坐标 d', '纵向：位置 T', '纵深：头 H'],
      ['横向：特征 D', '纵向：位置 T', '']
    ],
    steps: ['原始矩阵', '拆分特征轴', '交换头与位置轴', '换回轴顺序', '合头回到原矩阵'],
    descriptions: [
      '一个样本，三个位置，每个位置四个特征。先选中 4：它在位置 1 的第 0 个特征。',
      '把宽度 4 拆成 2 个头、每头 2 项，得到 [B,T,H,d]。前两项属于头 0，后两项属于头 1；数值没有改变。',
      '交换 T 和 H，得到 [B,H,T,d]。现在先选头，再选位置。每个头仍包含位置 0、1、2。',
      '合头前先把 H 和 T 换回去，让同一位置的各头重新相邻。仍然只有索引顺序改变。',
      '将每个位置的两个头按原顺序拼成四项，得到原来的 [B,T,D]。12 个数字逐项回到原位。'
    ],
    codes: ['X', 'X.reshape(B, T, H, d)', 'X.reshape(B, T, H, d).transpose(1, 2)',
      'heads.transpose(1, 2)', 'heads.transpose(1, 2).contiguous().reshape(B, T, D)']
  },
  en: {
    language: 'en', title: 'Split and merge heads',
    eyebrow: 'HELLO LLM / LESSON 12 · 3D TENSOR LAB', back: '← Back to the lesson',
    lead: 'Follow one number through splitting, transposing, and merging heads. Every head keeps every position; all 12 values stay unchanged.',
    shape: 'Current shape', trace: 'Track value', original: 'Original index', current: 'Current index', unchanged: 'The value stays unchanged',
    step: 'Step', previous: 'Previous', next: 'Next', replay: 'Restart', play: 'Play', pause: 'Pause',
    orbit: 'Free rotation', fixed: 'Fixed view', reset: 'Reset view', front: 'Front', angle: 'Angled', zoomIn: 'Zoom in', zoomOut: 'Zoom out',
    scene: 'Numbered 3D tensor. Use the number buttons below to select a coordinate.',
    loading: 'Preparing the 3D view…', ready: 'Fixed view · inspect one step at a time',
    orbitHelp: 'Drag to rotate; pinch to zoom. Step and number buttons also work.',
    fallback: '3D is unavailable on this device. The index table below still supports every step.',
    noScript: 'Enable JavaScript to explore the tensor, or open the full static diagram.',
    staticLink: 'Open the static split diagram', details: 'Index table & notes (scroll)', table: 'Select a number to inspect its index', value: 'Value', index: 'Index',
    head0: 'Head 0 · first two features', head1: 'Head 1 · last two features', selected: 'Outline · tracked value',
    scope: 'This lab only splits, transposes, and merges. It does not compute projections or attention. In full attention, Q/K/V are projected before splitting.',
    note: 'After splitting, the spatial directions represent position, head, and within-head coordinate. Their order changes by step; batch B=1 is fixed. Block thickness only separates cells, not an extra dimension.',
    source: 'Values come from the saved lesson 12 experiment. No training runs here.',
    axes: [
      ['x: feature D', 'y: position T', ''], ['x: within-head d', 'y: position T', 'z: head H'],
      ['x: within-head d', 'y: head H', 'z: position T'], ['x: within-head d', 'y: position T', 'z: head H'],
      ['x: feature D', 'y: position T', '']
    ],
    steps: ['Input', 'Split features', 'Swap axes', 'Restore order', 'Merge heads'],
    descriptions: [
      'One sample, three positions, four features per position. Start with 4: position 1, feature 0.',
      'Split width 4 into 2 heads of width 2, giving [B,T,H,d]. The first two features go to head 0; the last two to head 1. Values do not change.',
      'Swap T and H to get [B,H,T,d]. Index the head first, then the position. Each head still contains positions 0, 1, and 2.',
      'Before merging, swap H and T back so that all heads at the same position are adjacent again. Only index order changes.',
      'Concatenate both heads at each position in the original order to restore [B,T,D]. All 12 numbers return to their original slots.'
    ]
  }
};
COPY.en.codes = COPY.zh.codes;
