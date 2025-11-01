from abc import ABC, abstractmethod

from psutil import cpu_freq, cpu_percent, cpu_count, virtual_memory, disk_partitions, disk_usage, net_if_addrs, \
    net_io_counters
from platform import processor


class Component(ABC):
    @abstractmethod
    def get_info(self) -> dict:
        """Метод для получения общей информации и компоненте"""
        ...

    @abstractmethod
    def get_usage(self) -> dict:
        """Метод для получения информации о текущем состоянии использования компонента"""
        ...


class Processor(Component):
    """Класс для получения информации о процессоре"""

    def __init__(self):
        self.name = self.get_name()

    def get_name(self) -> str:
        return processor() or "Неизвестный процессор"

    def get_info(self):
        cores_physical, cores_logical = self.get_core_count()
        freq = cpu_freq()
        return {
            "name": self.name,
            "physical_cores": cores_physical,
            "logical_cores": cores_logical,
            "max_frequency": freq.max if freq else None,
        }

    def get_usage(self, interval=0.5):
        freq = cpu_freq()
        return {
            "usage_percent": cpu_percent(interval=interval),
            "current_frequency": freq.current if freq else None,
        }

    def get_core_count(self):
        return cpu_count(logical=False), cpu_count(logical=True)


class Memory(Component):
    """Класс для получения информации об оперативной памяти"""

    def get_info(self):
        mem = virtual_memory()
        return {"total": mem.total}

    def get_usage(self):
        mem = virtual_memory()
        return {
            "used": mem.used,
            "available": mem.available,
            "percent": mem.percent
        }


class Disk(Component):
    """Класс для получения информации о дисках"""

    def get_info(self):
        partitions = disk_partitions()
        return {
            "partitions": [p.device for p in partitions]
        }

    def get_usage(self, path="/"):
        """
        :param path: Путь к месту на диске, для получения информации
        :return: dict
        """
        disk = disk_usage(path)
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        }


class Network(Component):
    """Класс для получения информации о сети"""

    def get_info(self):
        addrs = net_if_addrs()
        return {"interfaces": list(addrs.keys())}

    def get_usage(self):
        net = net_io_counters()
        return {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv
        }


class GPU(Component):
    """Класс для получения информации о видеокарте (через GPUtil, если доступен)"""

    def __init__(self):
        try:
            import GPUtil
            self.GPUtil = GPUtil
        except ImportError:
            self.GPUtil = None

    def get_info(self):
        if not self.GPUtil:
            return {"error": "Библиотека GPUtil не установлена"}

        gpus = self.GPUtil.getGPUs()
        return [
            {"name": gpu.name, "driver": getattr(gpu, "driver", None)}
            for gpu in gpus
        ]

    def get_usage(self):
        if not self.GPUtil:
            return {"error": "Библиотека GPUtil не установлена"}

        gpus = self.GPUtil.getGPUs()
        gpu_data = []
        for gpu in gpus:
            gpu_data.append({
                "load_percent": gpu.load * 100,
                "memory_total": gpu.memoryTotal,
                "memory_used": gpu.memoryUsed,
                "temperature": gpu.temperature
            })
        return gpu_data


class SystemMonitor:
    """Общий класс, объединяющий все компоненты"""

    def __init__(self):
        self.cpu = Processor()
        self.memory = Memory()
        self.disk = Disk()
        self.network = Network()
        self.gpu = GPU()

    def get_all_info(self) -> dict[str, dict]:
        """Общая информация о компонентах"""
        return {
            "cpu": self.cpu.get_info(),
            "memory": self.memory.get_info(),
            "disk": self.disk.get_info(),
            "network": self.network.get_info(),
            "gpu": self.gpu.get_info(),
        }

    def get_all_usage(self) -> dict[str, dict]:
        """Текущее использование ресурсов"""
        return {
            "cpu": self.cpu.get_usage(),
            "memory": self.memory.get_usage(),
            "disk": self.disk.get_usage(),
            "network": self.network.get_usage(),
            "gpu": self.gpu.get_usage(),
        }

# if __name__ == "__main__":
#     monitor = SystemMonitor()
#     print("Общая информация:")
#     print(monitor.get_all_info())
#     print("\nТекущее использование:")
#     print(monitor.get_all_usage())
