from typing import Optional, Dict
import torch
from torch import Tensor
from fairseq.models import BaseFairseqModel
from omegaconf import OmegaConf
from speechgpt.logger import get_logger
from speechgpt.models.whisper.model import HuggingFaceWhisperModel
from speechgpt.models.qwen.model import HuggingFaceQwen2ForCausalLM

logger = get_logger()


class AsrLlmCascadeModel(BaseFairseqModel):
    """
    A cascade model that uses ASR (Automatic Speech Recognition) and LLM (Large Language Model) to generate text.

    The model consists of two components: an ASR model and an LLM model. The ASR model is used to generate text from
    speech, and the LLM model is used to generate text from the text generated by the ASR model.

    The model supports generating text from speech, generating text from text, and generating text from file.

    Args:
        args (dict): a dictionary of arguments, including the path to the model weights

    Attributes:
        asr (HuggingFaceWhisperModel): the ASR model
        asr_processor (AutoProcessor): the processor for the ASR model
        llm (HuggingFaceQwen2ForCausalLM): the LLM model
        llm_tokenizer (AutoTokenizer): the tokenizer for the LLM model
    """

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.asr = None
        self.llm = None
        self.asr_processor = None
        self.llm_tokenizer = None
        self.load_models(args)

    def load_models(self, args):
        logger.info("Loading models: ASR and LLM")
        try:
            self.asr = HuggingFaceWhisperModel.build_model(args, None)
            logger.info("ASR model loaded successfully")

            self.llm = HuggingFaceQwen2ForCausalLM.build_model(args, None)
            logger.info("LLM model loaded successfully")

            self.asr_processor = self.asr.processor
            self.llm_tokenizer = self.llm.tokenizer
            self.llm_tokenizer.add_special_tokens({'pad_token': '[PAD]'})
        except Exception as e:
            logger.error("Error loading models: %e", e)
            raise

    @classmethod
    def build_model(cls, args=None, task=None):
        logger.info("Building ASR-LLM Cascade Model")
        return cls(args)

    @staticmethod
    def add_args(parser):
        parser.add_argument('--asr_config', type=str, default='openai/whisper-large-v3-turbo')
        parser.add_argument('--llm_config', type=str, default='Qwen/Qwen2-0.5B')
        parser.add_argument('--local_asr_weights', type=str, default=None)
        parser.add_argument('--local_llm_weights', type=str, default=None)

    def forward(
            self,
            src_tokens: Tensor,
            tgt_tokens: Optional[Tensor] = None,
            incremental_state: Optional[Dict[str, Dict[str, Optional[Tensor]]]] = None,
    ):
        """
        Run the forward pass of the model.

        Args:
            src_tokens (Tensor): the input tokens
            tgt_tokens (Tensor, optional): the target tokens
            incremental_state (dict, optional): the incremental state

        Returns:
            a tuple containing the output of the ASR model and the output of the LLM model
        """
        logger.debug("Running forward pass")
        try:
            asr_output = self.asr(src_tokens, tgt_tokens, incremental_state)
            logger.debug("ASR output generated")
            return asr_output
        except Exception as e:
            logger.error("Error during forward pass: %e", e)
            raise

    @torch.no_grad()
    def generate_from_asr(
            self,
            input_tokens=None,
            text=False,
            skip_special_tokens=True,
            file=None,
            **kwargs
    ):
        """
        Generate text from the ASR model.

        Args:
            input_tokens (Tensor): the input tokens
            text (bool): whether to generate text or not
            skip_special_tokens (bool): whether to skip special tokens or not
            file (str): the file to generate text from
            **kwargs: additional arguments

        Returns:
            the generated text
        """
        if input_tokens is None and file is None:
            logger.error("Both input_tokens and file are None")
            raise ValueError("input_tokens or file must not be None")

        logger.info("Generating text from ASR")
        asr_output = self.asr.generate(input_tokens, text, skip_special_tokens, file, **kwargs)
        return asr_output

    @torch.no_grad()
    def generate(
            self,
            logger,
            input_tokens=None,
            skip_special_tokens=True,
            file=None,
            prompt=None,
            **kwargs
    ):
        """
        Generate text from the ASR and LLM models.

        Args:
            input_tokens (Tensor): the input tokens
            logger (logging.Logger): the logger
            skip_special_tokens (bool): whether to skip special tokens or not
            file (str): the file to generate text from
            **kwargs: additional arguments

        Returns:
            the generated text
        """
        if input_tokens is None and file is None and prompt is None:
            logger.error("All of input_tokens, file, prompt are None")
            raise ValueError("One of input_tokens or file or prompt must not be None")

        try:
            if input_tokens is not None or file is not None:
                is_text = True
                asr_texts = self.asr.generate(input_tokens, is_text, skip_special_tokens, file)
                logger.info("Generated asr_texts %s", asr_texts)
            else:
                asr_texts = [""]

            if prompt is not None:
                asr_texts = [f"{prompt}\n\n{txt}" for txt in asr_texts]

            llm_tok_outs = self.llm_tokenizer(asr_texts, padding=True, return_tensors="pt")
            generate_ids = self.llm.generate(llm_tok_outs.input_ids, attention_mask=llm_tok_outs.attention_mask,
                                             max_new_tokens=150, do_sample=True, top_k=50, top_p=0.95)
            gen_texts = self.llm_tokenizer.batch_decode(generate_ids, skip_special_tokens=True,
                                                        clean_up_tokenization_spaces=False)
            logger.debug("Generated text successfully")
            return gen_texts
        except Exception as e:
            logger.error("Error during generation: %e", e)
            raise

    def get_text(self):
        return "text"


def get_cascade_model():
    logger.info("Initializing cascade model")
    args = OmegaConf.create()
    args.llm_config = "Qwen/Qwen2-0.5B"
    args.asr_config = "openai/whisper-large-v3-turbo"
    cascade = AsrLlmCascadeModel.build_model(args)
    logger.info("Cascade model initialized successfully")
    return cascade


if __name__ == '__main__':
    _ = get_cascade_model()
