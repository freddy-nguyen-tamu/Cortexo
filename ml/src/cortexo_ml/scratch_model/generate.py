import torch

@torch.no_grad()
def generate(
    model,
    input_ids,
    max_new_tokens=128,
    temperature=0.8,
    top_k=50,
):
    model.eval()

    for _ in range(max_new_tokens):
        x = input_ids[:, -model.cfg.max_seq_len:]
        logits = model(x)["logits"][:, -1, :]

        if temperature <= 0:
            next_token = logits.argmax(dim=-1, keepdim=True)
        else:
            logits = logits / temperature

            if top_k:
                values, _ = torch.topk(
                    logits,
                    min(top_k, logits.size(-1)),
                )
                cutoff = values[:, [-1]]
                logits = torch.where(
                    logits < cutoff,
                    torch.full_like(logits, float("-inf")),
                    logits,
                )

            probs = torch.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)

        input_ids = torch.cat([input_ids, next_token], dim=1)

    return input_ids