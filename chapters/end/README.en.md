# Closing Thoughts | You Can Now Explain Those “Red Apples”

Build a Small Model, Understand Large Models · Closing article

At the beginning, we gave the model half a sentence: “早上，小丁喜欢” (“In the morning, Xiaoding likes”). At first it produced a string of nonsense. After training, it could write “红色的苹果。” (“red apples.”). It then struggled when we switched to a question. Only after further fine-tuning did it begin answering in the requested format.

Back then, we saw a few pieces of text. Now look at generation again:

![With pretrained parameters fixed, each selected character enters the new context, until the end marker is selected.](../18-generation/images/en/过程.gif)

The context changes. The candidate scores change. The parameters remain the same saved set throughout. Training changes those parameters; generation uses a chosen set of parameters to keep processing new inputs. You can now explain the two processes from the opening article separately by following the code.

## Which parts can you now inspect?

Previously, a model may have looked like an interface that takes a sentence and returns a sentence. Across these 20 lessons, we opened several important parts inside that interface.

Character IDs select table rows, and vectors take part in calculations. Attention reads the preceding context it is allowed to use, while positional information brings order into the computation. Model blocks connect these steps, and the model finally scores the vocabulary candidates. During training, loss measures prediction error, backpropagation computes gradients, and an optimizer updates parameters.

All of this ends up in one project. Random weights can start pretraining; saved pretrained weights can generate text or continue into question–answer fine-tuning. The components from individual lesson experiments have become parts of a complete model.

## Keep a record of your own reasoning

The two practical tasks in Lesson 20 can leave you with two different results. The fact-swap experiment lets you trace how data changes parameters. The “Xiaotang and oranges” task asks you to reconnect the vocabulary, labels, model dimensions, and evaluation questions. The comparisons in Lesson 19 also remind us to check what an improvement in one ability costs another.

Keep your code, data, weights, and experiment notes together. When you return later, you should be able to find what you predicted, what actually happened, which record supports your explanation, and which claim still lacks evidence. Such a record stands up to review better than a screenshot that only says “training succeeded.”

## Choose one direction to explore next

**To see whether a model can learn your own text, start by changing a small corpus.** Prepare a few hundred short sentences you have the right to use, and hold out some whole sentences for validation. The current project generates data from a fixed set of people and fruits. You need to change those generation rules, rebuild the vocabulary, and check the maximum sentence length. Dropping a text file into the directory does not automatically create a training task. In your first run, change only the data and compare training loss, held-out loss, and actual outputs.

**To make an existing model perform a task, continue studying task fine-tuning.** For example, you might turn product descriptions into fixed fields. Prepare correct input–output examples and hold out a set of questions. Compare giving the model task instructions directly with its behavior after fine-tuning. This course uses full supervised fine-tuning. For larger models, you can also study [LoRA](https://arxiv.org/abs/2106.09685), then decide whether your memory budget, data, and task suit that approach.

**To understand a real publicly available model, start from familiar components.** Inspect how it splits tokens, how wide its representations are, and how its attention is organized. Then look at how it reuses earlier computation when generating the next item. Lessons 16 and 18 provide starting points for examining real models and KV caches. For each new design, ask which specific limitation it addresses, then check the implementation.

These directions can also lead to a small application, such as answering questions about your own notes. First distinguish missing information from poor answers despite having the information. Then decide what to retrieve, whether fine-tuning is needed, and how to check the responses.

Save your current results, then change one condition. When you encounter an unfamiliar model, you can investigate it just as you traced the row for “欢”: follow the input, ask what information it read, find which calculation changed the result, and determine which parameters training changed.

Next time, continue with a question an experiment can test.

<!-- chapter-navigation:start -->

---

[← The full workflow and checks of the principles](../20-full-workflow/README.en.md) · [Contents](../../README.en.md#course-contents)

<!-- chapter-navigation:end -->
