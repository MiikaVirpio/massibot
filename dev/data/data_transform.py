import pandas as pd
df = pd.read_csv("../../bot/dataset.csv")

def chat_format(row):
    return {
        "messages": [
            {"role": "user", "content": row["question"]},
            {"role": "assistant", "content": row["answer"]}
        ]
    }

chat_df = df.apply(chat_format, axis=1)
chat_df.to_json("semigenerated1.jsonl", orient="records", lines=True)