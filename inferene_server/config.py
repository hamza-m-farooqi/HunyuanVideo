import re


class OptionsDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'OptionsDict' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(f"'OptionsDict' object has no attribute '{name}'")


def add_network_options(options: OptionsDict):
    options.model = "HYVideo-T/2-cfgdistill"
    options.latent_channels = 16
    options.precision = "bf16"
    options.rope_theta = 256


def add_extra_models_options(options: OptionsDict):
    # VAE Related
    options.vae = "884-16c-hy"
    options.vae_precision = "fp16"
    options.vae_tiling = True
    options.text_encoder = "llm"
    options.text_encoder_precision = "fp16"
    options.text_states_dim = 4096
    options.text_len = 256
    options.tokenizer = "llm"
    options.prompt_template = "dit-llm-encode"
    options.prompt_template_video = "dit-llm-encode-video"
    options.hidden_state_skip_layer = 2
    options.apply_final_norm = False
    # CLIP Related
    options.text_encoder_2 = "clipL"
    options.text_encoder_precision_2 = "fp16"
    options.text_states_dim_2 = 768
    options.tokenizer_2 = "clipL"
    options.text_len_2 = 77


def add_denoise_schedule_options(options: OptionsDict):
    options.denoise_type = "flow"
    options.flow_shift = 7.0
    options.flow_reverse = False
    options.flow_solver = "euler"
    options.use_linear_quadratic_schedule = False
    options.linear_schedule_end = 25


def add_inference_options(options: OptionsDict):
    # Model Loading options
    options.model_base = "ckpts"
    options.dit_weight = (
        "ckpts/hunyuan-video-t2v-720p/transformers/mp_rank_00_model_states.pt"
    )
    options.model_resolution = "720p"  # 720p or 540p
    options.load_key = "module"
    options.use_cpu_offload = False

    # Inference general options
    options.batch_size = 1
    options.setdefault("infer_steps", 50)
    options.disable_autocast = False
    options.save_path = "./results"
    options.save_path_suffix = ""
    options.name_suffix = ""
    options.setdefault("num_videos", 1)
    options.video_length = 129
    options.seed_type = "auto"  # auto | file | random | fixed
    # options.seed=None
    # options.neg_prompt=""
    options.cfg_scale = (
        1  # on some blogs it is suggested to keep cfg above 6 as it is faster this way
    )
    options.embedded_cfg_scale = 6
    options.use_fp8 = False
    options.reproduce = False
    options.setdefault("ulysses_degree", 1)
    options.setdefault("ring_degree", 1)


def sanity_check_args(options: OptionsDict):
    # VAE channels
    vae_pattern = r"\d{2,3}-\d{1,2}c-\w+"
    if not re.match(vae_pattern, options.vae):
        raise ValueError(
            f"Invalid VAE model: {options.vae}. Must be in the format of '{vae_pattern}'."
        )
    vae_channels = int(options.vae.split("-")[1][:-1])
    if options.latent_channels is None:
        options.latent_channels = vae_channels
    if vae_channels != options.latent_channels:
        raise ValueError(
            f"Latent channels ({options.latent_channels}) must match the VAE channels ({vae_channels})."
        )
    return options


def add_all_options(options: OptionsDict):
    add_network_options(options)
    add_extra_models_options(options)
    add_denoise_schedule_options(options)
    add_inference_options(options)
    sanity_check_args(options)
    return options
