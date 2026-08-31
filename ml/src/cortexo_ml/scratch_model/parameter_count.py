def count_parameters(model):
    return {
        "total": sum(p.numel() for p in model.parameters()),
        "trainable": sum(
            p.numel() for p in model.parameters()
            if p.requires_grad
        ),
    }