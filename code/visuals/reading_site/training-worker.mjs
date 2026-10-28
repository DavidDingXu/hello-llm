const engineModule = import(new URL('./training-engine.mjs' + new URL(import.meta.url).search, import.meta.url));
let engine, busy = false;
self.onmessage = async ({data}) => {
  if (data.type !== 'start' || busy) return;
  busy = true;
  const send = value => self.postMessage({...value, id: data.id});
  try {
    if (!engine) {
      send({type: 'loading'});
      const {TrainingEngine} = await engineModule;
      engine = await TrainingEngine.create();
    }
    send({type: 'ready'});
    const report = await engine.run(data.options, send);
    send({type: 'complete', report});
  } catch (error) {
    send({type: 'error', error: String(error), sampleError: error.sampleError});
  } finally { busy = false; }
};
