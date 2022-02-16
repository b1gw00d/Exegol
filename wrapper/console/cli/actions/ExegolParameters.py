from wrapper.console.cli.actions.Command import Command
from wrapper.console.cli.actions.GenericParameters import *
from wrapper.manager.ExegolManager import ExegolManager
from wrapper.utils.ExeLog import logger


class Start(Command, ContainerCreation, ContainerStart):
    """Automatically create, start / resume and enter an Exegol container"""

    def __init__(self):
        Command.__init__(self)
        ContainerCreation.__init__(self, self.groupArgs)
        ContainerStart.__init__(self, self.groupArgs)

        self._usages = {
            "Start interactively a container": "exegol start",
            "Create a 'demo' container using 'stable' image": "exegol start [green]demo[/green] [orange3]stable[/orange3]",
            "Spawn a shell from 'demo' container": "exegol start [green]demo[/green]",
            "Create a container 'htb' with a VPN": "exegol start [green]htb[/green] [orange3]stable[/orange3] --vpn ~/vpn/lab_Dramelac.ovpn",
            "Create a container 'test' with a custom shared workspace": "exegol start [green]test[/green] [orange3]stable[/orange3] -w ./project/pentest",
            "Create a container 'test' sharing the current working directory": "exegol start [green]test[/green] [orange3]stable[/orange3] -cwd",
            "Create a container 'app' with custom volume": "exegol start [green]app[/green] [orange3]stable[/orange3] -V '/var/app/:/app/'",
            "Get a tmux shell": "exegol start --shell tmux",
            "Use a Proxmark": "exegol start -d /dev/ttyACM0",
            "Use a LOGITacker": "exegol start -d /dev/ttyACM0",
            "Use an ACR122u": "exegol start -d /dev/bus/usb/",
            "Use an HackRF One": "exegol start -d /dev/bus/usb/",
            "Use an Crazyradio PA": "exegol start -d /dev/bus/usb/",
        }

        # Create container start / exec arguments
        self.shell = Option("-s", "--shell",
                            dest="shell",
                            action="store",
                            choices={"zsh", "bash", "tmux"},
                            default="zsh",
                            help="Select a shell environment to launch at startup (Default: [blue]zsh[/blue])")

        # Create group parameter for container selection
        self.groupArgs.append(GroupArg({"arg": self.shell, "required": False},
                                       title="[bold cyan]Start[/bold cyan] [blue]specific options[/blue]"))

    def __call__(self, *args, **kwargs):
        return ExegolManager.start


class Stop(Command, ContainerSelector):
    """Stop an Exegol container in a saved state"""

    def __init__(self):
        Command.__init__(self)
        ContainerSelector.__init__(self, self.groupArgs)

        self._usages = {
            "Stop interactively one or multiple container": "exegol stop",
            "Stop 'demo'": "exegol stop demo"
        }

    def __call__(self, *args, **kwargs):
        logger.debug("Running stop module")
        return ExegolManager.stop


class Install(Command, ImageSelector):
    """Install or build Exegol image"""

    def __init__(self):
        Command.__init__(self)
        ImageSelector.__init__(self, self.groupArgs)

        self._usages = {
            "Install or build interactively an exegol image": "exegol install",
            "Install or update the 'stable' image": "exegol install [orange3]stable[/orange3]",
            "Build 'local' image": "exegol install [orange3]local[/orange3]"
        }

    def __call__(self, *args, **kwargs):
        logger.debug("Running install module")
        return ExegolManager.install


class Update(Command, ImageSelector):
    """Update an Exegol image"""

    def __init__(self):
        Command.__init__(self)
        ImageSelector.__init__(self, self.groupArgs)

        self._usages = {
            "Install or update interactively an exegol image": "exegol update",
            "Install or update the 'stable' image": "exegol update [orange3]stable[/orange3]"
        }

    def __call__(self, *args, **kwargs):
        logger.debug("Running update module")
        return ExegolManager.update


class Uninstall(Command, ImageSelector):
    """Remove Exegol [default not bold]image(s)[/default not bold]"""

    def __init__(self):
        Command.__init__(self)
        ImageSelector.__init__(self, self.groupArgs)

        self._usages = {
            "Uninstall interactively one or many exegol image": "exegol uninstall",
            "Uninstall the 'dev' image": "exegol uninstall [orange3]dev[/orange3]"
        }

    def __call__(self, *args, **kwargs):
        logger.debug("Running uninstall module")
        return ExegolManager.uninstall


class Remove(Command, ContainerSelector):
    """Remove Exegol [default not bold]container(s)[/default not bold]"""

    def __init__(self):
        Command.__init__(self)
        ContainerSelector.__init__(self, self.groupArgs)

        self._usages = {
            "Remove interactively one or many container": "exegol remove",
            "Remove the 'demo' container": "exegol remove [green]demo[/green]"
        }

    def __call__(self, *args, **kwargs):
        logger.debug("Running remove module")
        return ExegolManager.remove


class Exec(Command, ContainerCreation, ContainerStart):
    """Execute a command on an Exegol container"""

    def __init__(self):
        Command.__init__(self)
        ContainerCreation.__init__(self, self.groupArgs)
        ContainerStart.__init__(self, self.groupArgs)

        self._usages = {
            "Execute the command 'bloodhound' in the container 'main'": "exegol exec [green]main[/green] bloodhound",
            "Execute the command 'bloodhound' in a temporary container based on the 'stable' image": "exegol exec --tmp [orange3]stable[/orange3] bloodhound",
            "Execute the command 'nmap -h' with console output": "exegol exec -v [green]main[/green] 'nmap -h'",
            "Execute the command 'bloodhound' in background": "exegol exec -b [green]main[/green] bloodhound",
            "Execute a command in background with a temporary container": "exegol exec -b --tmp [green]stable[/green] bloodhound",
        }

        # Overwrite default selectors
        for group in self.groupArgs.copy():
            # Find group containing default selector to remove them
            for parameter in group.options:
                if parameter.get('arg') == self.containertag or parameter.get('arg') == self.imagetag:
                    # Removing default GroupArg selector
                    self.groupArgs.remove(group)
                    break
        # Removing default selector objects
        self.containertag = None
        self.imagetag = None

        self.selector = Option("selector",
                               metavar="CONTAINER or IMAGE",
                               nargs='?',
                               action="store",
                               help="Tag used to target an Exegol container (by default) or an image (if --tmp is set).")

        # Custom parameters
        self.exec = Option("exec",
                           metavar="COMMAND",
                           nargs="+",
                           action="store",
                           help="Execute a single command in the exegol container.")
        self.daemon = Option("-b", "--background",
                             action="store_true",
                             dest="daemon",
                             help="Executes the command in background as a daemon "
                                  "(default: [red bold not italic]False[/red bold not italic])")
        self.tmp = Option("--tmp",
                          action="store_true",
                          dest="tmp",
                          help="Created a dedicated and temporary container to execute the command "
                               "(default: [red bold not italic]False[/red bold not italic])")

        # Create group parameter for container selection
        self.groupArgs.append(GroupArg({"arg": self.selector, "required": False},
                                       {"arg": self.exec, "required": False},
                                       {"arg": self.daemon, "required": False},
                                       {"arg": self.tmp, "required": False},
                                       title="[bold cyan]Exec[/bold cyan] [blue]specific options[/blue]"))

    def __call__(self, *args, **kwargs):
        logger.debug("Running exec module")
        return ExegolManager.exec


class Info(Command):
    """Print info on containers and local & remote images (name, size, state, ...)"""

    def __init__(self):
        super().__init__()
        self._usages = {
            "Print containers and images essentials information": "exegol info",
            "Print advanced information": "exegol info -v",
            "Print full information": "exegol info -vv"
        }

    def __call__(self, *args, **kwargs):
        return ExegolManager.info


class Version(Command):
    """Print current Exegol version"""

    def __call__(self, *args, **kwargs):
        return ExegolManager.print_version