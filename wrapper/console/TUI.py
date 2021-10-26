import logging
import re

from rich import box
from rich.progress import TextColumn, BarColumn, TransferSpeedColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.prompt import Prompt
from rich.table import Table

from wrapper.console.ExegolProgress import ExegolProgress
from wrapper.console.LayerTextColumn import LayerTextColumn
from wrapper.model.ExegolContainer import ExegolContainer
from wrapper.model.ExegolImage import ExegolImage
from wrapper.model.SelectableInterface import SelectableInterface
from wrapper.utils.ExeLog import logger, console, ExeLog


class ExegolTUI:

    @staticmethod
    def downloadDockerLayer(stream, quick_exit=False):
        """Rich interface for docker image layer download from SDK stream"""
        layers = set()
        layers_downloaded = set()
        layers_extracted = set()
        downloading = {}
        extracting = {}
        # Create progress bar with columns
        with ExegolProgress(TextColumn("{task.description}", justify="left"),
                            BarColumn(bar_width=None),
                            "[progress.percentage]{task.percentage:>3.1f}%",
                            "•",
                            LayerTextColumn("[bold]{task.completed}/{task.total}", "layer"),
                            "•",
                            TransferSpeedColumn(),
                            "•",
                            TimeElapsedColumn(),
                            "•",
                            TimeRemainingColumn(),
                            transient=True) as progress:
            task_layers_download = progress.add_task("[bold red]Downloading layers...", total=0)
            task_layers_extract = progress.add_task("[bold gold1]Extracting layers...", total=0, start=False)
            for line in stream:  # Receiving stream from docker API
                status = line.get("status", '')
                layer_id = line.get("id")
                if status == "Pulling fs layer":  # Identify new layer to download
                    layers.add(layer_id)
                    progress.update(task_layers_download, total=len(layers))
                    progress.update(task_layers_extract, total=len(layers))
                elif "Pulling from " in status:  # Rename task with image name
                    progress.getTask(task_layers_download).description = \
                        f"[bold red]Downloading {status.replace('Pulling from ', '')}:{line.get('id', 'latest')}"
                    progress.getTask(task_layers_extract).description = \
                        f"[bold gold1]Extracting {status.replace('Pulling from ', '')}:{line.get('id', 'latest')}"
                elif status == "Download complete" or status == "Pull complete":  # Mark task as complete and remove it from the pool
                    # Select task / layer pool depending on the status
                    task_pool = downloading
                    layer_pool = layers_downloaded
                    if status == "Pull complete":
                        task_pool = extracting
                        layer_pool = layers_extracted
                    # Tagging current layer as ended
                    layer_pool.add(layer_id)
                    # Remove finished layer progress bar
                    layer_task = task_pool.get(layer_id)
                    if layer_task is not None:
                        progress.remove_task(layer_task)  # Remove progress bar
                        task_pool.pop(layer_id)  # Remove task from pool
                    # Update global task completion status
                    progress.update(task_layers_download, completed=len(layers_downloaded))
                    progress.update(task_layers_extract, completed=len(layers_extracted))
                elif status == "Downloading" or status == "Extracting":  # Handle download or extract progress
                    task_pool = downloading
                    if status == "Extracting":
                        task_pool = extracting
                        if not progress.getTask(task_layers_extract).started:
                            progress.start_task(task_layers_extract)
                    task_id = task_pool.get(layer_id)
                    if task_id is None:  # If this is a new layer, create a new task accordingly
                        task_id = progress.add_task(
                            f"[{'blue' if status == 'Downloading' else 'green'}]{status} {layer_id}",
                            total=line.get("progressDetail", {}).get("total", 100),
                            layer=layer_id)
                        task_pool[layer_id] = task_id
                    progress.update(task_id, completed=line.get("progressDetail", {}).get("current", 100))
                elif "Image is up to date" in status or "Status: Downloaded newer image for" in status:
                    logger.success(status)
                    if quick_exit:
                        break
                else:
                    logger.debug(line)

    @staticmethod
    def buildDockerImage(build_stream):
        """Rich interface for docker image building from SDK stream"""
        for line in build_stream:
            stream_text = line.get("stream", '')
            if stream_text.strip() != '':
                if "Step" in stream_text:
                    logger.info(stream_text.rstrip())
                elif "--->" in stream_text or \
                        "Removing intermediate container " in stream_text or \
                        re.match(r"Successfully built [a-z0-9]{12}", stream_text) or \
                        re.match(r"^Successfully tagged ", stream_text):
                    logger.verbose(stream_text.rstrip())
                else:
                    logger.raw(stream_text, level=logging.DEBUG)
            if ': FROM ' in stream_text:
                logger.info("Downloading docker image")
                ExegolTUI.downloadDockerLayer(build_stream, quick_exit=True)

    @staticmethod
    def printTable(data: list, title: str = None):
        """Printing Rich table for a list of object"""
        table = Table(title=title, show_header=True, header_style="bold blue", border_style="grey35",
                      box=box.SQUARE_DOUBLE_HEAD)
        if len(data) == 0:
            logger.info("No data supplied")
            # TODO handle no data
            return
        else:
            if type(data[0]) is ExegolImage:
                ExegolTUI.__buildImageTable(table, data)
            elif type(data[0]) is ExegolContainer:
                ExegolTUI.__buildContainerTable(table, data)
            elif type(data[0]) is str:
                ExegolTUI.__buildStringTable(table, data, title)
            else:
                logger.error(f"Print table of {type(data[0])} is not implemented")
                raise NotImplementedError
        console.print(table)

    @staticmethod
    def __buildImageTable(table, data: [ExegolImage]):
        """Building Rich table from a list of ExegolImage"""
        table.title = "Available images"
        # Define columns
        verbose_mode = logger.isEnabledFor(ExeLog.VERBOSE)
        if verbose_mode:
            table.add_column("Id")
        table.add_column("Image tag")
        if verbose_mode:
            table.add_column("Download size")
            table.add_column("Disk size")
        else:
            # Depending on whether the image has already been downloaded or not,
            # it will show the download size or the size on disk
            table.add_column("Size")
        table.add_column("Status")
        table.add_column("Type")
        # Load data into the table
        for image in data:
            if verbose_mode:
                table.add_row(image.getId(), image.getName(), image.getDownloadSize(), image.getRealSize(),
                              image.getStatus(), image.getType())
            else:
                table.add_row(image.getName(), image.getSize(), image.getStatus(), image.getType())

    @staticmethod
    def __buildContainerTable(table, data: [ExegolContainer]):
        """Building Rich table from a list of ExegolContainer"""
        table.title = "[gold3][g]Available containers[/g][/gold3]"
        # Define columns
        verbose_mode = logger.isEnabledFor(ExeLog.VERBOSE)
        debug_mode = logger.isEnabledFor(logging.DEBUG)
        if verbose_mode:
            table.add_column("Id")
        table.add_column("Container tag")
        table.add_column("State")
        table.add_column("Image tag")
        table.add_column("Configurations")
        if verbose_mode:
            table.add_column("Mounts")
            table.add_column("Devices")
            table.add_column("Envs")
        # Load data into the table
        for container in data:
            if verbose_mode:
                table.add_row(container.getId(), container.name, container.getTextStatus(), container.image.getName(),
                              container.config.getTextFeatures(), container.config.getTextMounts(debug_mode),
                              container.config.getTextDevices(debug_mode), container.config.getTextEnvs(debug_mode))
            else:
                table.add_row(container.name, container.getTextStatus(), container.image.getName(),
                              container.config.getTextFeatures())

    @staticmethod
    def __buildStringTable(table, data: [str], title: str = "Key"):
        """Building a simple Rich table from a list of string"""
        table.title = None
        # Define columns
        table.add_column(title)
        # Load data into the table
        for string in data:
            table.add_row(string)

    @classmethod
    def selectFromTable(cls, data: [SelectableInterface], object_type=None, default=None) -> SelectableInterface:
        """Return an object (implementing SelectableInterface) selected by the user
        Raise IndexError of the data list is empty."""
        if len(data) == 0:
            if object_type is ExegolImage:
                logger.warning("No images were found")
            elif object_type is ExegolContainer:
                logger.warning("No container were found")
            else:
                logger.warning("No container were found")
            raise IndexError
        cls.printTable(data)
        choices = [obj.getKey() for obj in data]
        if default is None:
            default = choices[0]  # TODO custom default choice
        choice = Prompt.ask("[blue][?][/blue] Select an object by his name", default=default, choices=choices,
                            show_choices=False)
        for o in data:
            if choice == o:
                return o
        logger.critical(f"Unknown error, cannot fetch selected object.")

    @classmethod
    def selectFromList(cls, data: iter, subject="an option", title="Options", default=None) -> str:
        """if data is list(str): Return a string selected by the user
        if data is dict: list keys and return corresponding value
        Raise IndexError of the data list is empty."""
        if len(data) == 0:
            logger.warning("No options were found")
            raise IndexError
        if type(data) is dict:
            submit_data = list(data.keys())
        else:
            submit_data = data
        cls.printTable(submit_data, title=title)
        if default is None:
            default = submit_data[0]
        choice = Prompt.ask(f"[blue][?][/blue] Select {subject}", default=default, choices=submit_data,
                            show_choices=False)
        if type(data) is dict:
            return data[choice]
        else:
            return choice