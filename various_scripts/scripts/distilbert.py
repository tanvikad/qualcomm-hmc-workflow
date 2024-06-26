import tensorflow as tf

from transformers import TensorType
from transformers import TFAutoModelForQuestionAnswering, AutoTokenizer
import sys

bs = 1
SEQ_LEN = 384
MODEL_NAME = "distilbert-base-uncased-distilled-squad"

# Allocate tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = TFAutoModelForQuestionAnswering.from_pretrained(MODEL_NAME, from_pt=True)

def model_fn(input_ids, attention_mask):
    output = model(input_ids, attention_mask)
    return (output.start_logits, output.end_logits)

model_fn = tf.function(
    model_fn,
    input_signature=[
        tf.TensorSpec(shape=[bs, SEQ_LEN], dtype=tf.int32) ,
        tf.TensorSpec(shape=[bs, SEQ_LEN], dtype=tf.int32)
    ]
)

# Sample input
context = "The government of France is based in Paris. Another famous city is Nice, in the south of France."
question = "What is the capital of France?"

input_encodings = tokenizer(
            question,
            context,
            return_tensors=TensorType.TENSORFLOW,
            # return_tensors="np",
            padding='max_length',
            return_length=True,
            max_length=SEQ_LEN,
            return_special_tokens_mask=True
        )

print(f"\nContext = \n{context}")
print(f"\nQ. > {question}")
start_logits, end_logits = model_fn(input_encodings.input_ids, input_encodings.attention_mask)

print("start_logits:", start_logits)
print("end_logits:", end_logits)

answer_start_index = int(tf.math.argmax(start_logits, axis=-1)[0])
answer_end_index = int(tf.math.argmax(end_logits, axis=-1)[0])

predict_answer_tokens = input_encodings.input_ids[0, answer_start_index : answer_end_index + 1]
ans = tokenizer.decode(predict_answer_tokens)
print(f"Prediction: {ans}\n")

from tensorflow.python.framework.convert_to_constants import convert_variables_to_constants_v2
frozen_func = convert_variables_to_constants_v2(model_fn.get_concrete_function())

layers = [op.name for op in frozen_func.graph.get_operations()]
print("-" * 50)
print("NO. of Frozen model layers: {}".format(len(layers)))

print("-" * 50)
print("Frozen model inputs: ")
print(frozen_func.inputs)
print("Frozen model outputs: ")
print(frozen_func.outputs)

graph_def = frozen_func.graph.as_graph_def()

graph_def = tf.compat.v1.graph_util.remove_training_nodes(graph_def)

tf.io.write_graph(graph_or_graph_def=graph_def,
                  logdir="/workspace/qualcomm-hmc-workflow/Quantization_Scripts/frozen_models",
                  name="distilbert-uncased-distilled.pb",
                  as_text=False)
