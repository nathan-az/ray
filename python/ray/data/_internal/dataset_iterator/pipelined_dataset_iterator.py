from typing import Any, TYPE_CHECKING, Callable, Optional, Union, Iterator, Tuple

from ray.types import ObjectRef
from ray.data.block import Block, BlockMetadata, DataBatch
from ray.data.dataset_iterator import DatasetIterator
from ray.data._internal.stats import DatasetStats

if TYPE_CHECKING:
    import pyarrow
    from ray.data import DatasetPipeline


class PipelinedDatasetIterator(DatasetIterator):
    def __init__(
        self,
        base_dataset_pipeline: "DatasetPipeline",
    ):
        self._base_dataset_pipeline = base_dataset_pipeline
        self._epoch_iterator = None

    def __repr__(self) -> str:
        return f"DatasetIterator({self._base_dataset_pipeline})"

    def _get_next_dataset(self) -> "DatasetPipeline":
        if self._epoch_iterator is None:
            self._epoch_iterator = self._base_dataset_pipeline.iter_epochs()

        ds = next(self._epoch_iterator)
        return ds

    def _to_block_iterator(
        self,
    ) -> Tuple[
        Iterator[Tuple[ObjectRef[Block], BlockMetadata]], Optional[DatasetStats]
    ]:
        epoch_pipeline = self._get_next_dataset()

        def block_iter():
            for ds in epoch_pipeline.iter_datasets():
                yield from ds._plan.execute().iter_blocks_with_metadata()

        return block_iter(), None

    def iter_batches(
        self,
        *,
        prefetch_batches: int = 0,
        batch_size: int = 256,
        batch_format: Optional[str] = "default",
        drop_last: bool = False,
        local_shuffle_buffer_size: Optional[int] = None,
        local_shuffle_seed: Optional[int] = None,
        _collate_fn: Optional[Callable[[DataBatch], Any]] = None,
        # Deprecated.
        prefetch_blocks: int = 0,
    ) -> Iterator[DataBatch]:
        # Set prefetch_batches to default of 0 for DatasetPipeline.
        return super().iter_batches(
            prefetch_batches=prefetch_batches,
            batch_size=batch_size,
            batch_format=batch_format,
            drop_last=drop_last,
            local_shuffle_buffer_size=local_shuffle_buffer_size,
            local_shuffle_seed=local_shuffle_seed,
            _collate_fn=_collate_fn,
            prefetch_blocks=prefetch_blocks,
        )

    def stats(self) -> str:
        return self._base_dataset_pipeline.stats()

    def schema(self) -> Union[type, "pyarrow.lib.Schema"]:
        return self._base_dataset_pipeline.schema()

    def __getattr__(self, name):
        if name == "_base_dataset_pipeline":
            raise AttributeError

        if hasattr(self._base_dataset_pipeline, name) and not name.startswith("_"):
            # Raise error for backwards compatibility.
            # TODO: remove this method in 2.6.
            raise DeprecationWarning(
                "session.get_dataset_shard returns a ray.data.DatasetIterator "
                "instead of a Dataset/DatasetPipeline as of Ray v2.3. "
                "Use iter_torch_batches(), to_tf(), or iter_batches() to "
                "iterate over one epoch. See "
                "https://docs.ray.io/en/latest/data/api/dataset_iterator.html "
                "for full DatasetIterator docs."
            )
        else:
            raise AttributeError()
