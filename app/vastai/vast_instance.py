from tabulate import tabulate
import logging

# Set up logging for SSH data tracking
logger = logging.getLogger(__name__)

class VastInstance:
    def __init__(self, instance_id, offer_id, client):
        self.instance_id = instance_id
        self.offer_id = offer_id
        self.client = client

    def _validate_ssh_data(self, instance_data):
        """Validate SSH data integrity and log any inconsistencies"""
        ssh_host = instance_data.get("ssh_host")
        ssh_port = instance_data.get("ssh_port")
        
        # Log SSH data for debugging
        logger.info(f"SSH data for instance {self.instance_id}: host='{ssh_host}', port={ssh_port}")
        
        # Check for suspicious SSH host patterns that might indicate incorrect data
        if ssh_host and isinstance(ssh_host, str):
            if ssh_host.startswith("ssh") and ".vast.ai" in ssh_host:
                logger.warning(f"Suspicious SSH host detected for instance {self.instance_id}: {ssh_host}")
                logger.warning(f"Expected format: IP address, got: {ssh_host}")
        
        # Check for suspicious SSH port patterns
        if ssh_port and isinstance(ssh_port, (int, str)):
            try:
                port_num = int(ssh_port)
                if port_num > 30000:  # Ports above 30000 might be mapped/forwarded ports
                    logger.warning(f"High SSH port detected for instance {self.instance_id}: {port_num}")
            except (ValueError, TypeError):
                logger.error(f"Invalid SSH port format for instance {self.instance_id}: {ssh_port}")
        
        return ssh_host, ssh_port

    def show(self):
        data = self.client.show_instance(self.instance_id).get("instances", {})
        
        # Validate SSH data for consistency
        ssh_host, ssh_port = self._validate_ssh_data(data)
        
        summary = {
            "Instance ID": data.get("id"),
            "Status": data.get("cur_state"),
            "GPU": data.get("gpu_name"),
            "GPU Count": data.get("num_gpus"),
            "GPU RAM (GB)": round(data.get("gpu_ram", 0) / 1024, 1),
            "CPU": data.get("cpu_name"),
            "CPU Cores": data.get("cpu_cores_effective"),
            "Disk (GB)": data.get("disk_space"),
            "Upload (Mbps)": data.get("inet_up"),
            "Download (Mbps)": data.get("inet_down"),
            "Public IP": data.get("public_ipaddr"),
            "SSH Host": ssh_host,
            "SSH Port": ssh_port,
            "Template": data.get("template_name"),
            "Geolocation": data.get("geolocation"),
            "OS": data.get("os_version"),
        }
        print("\n🖥️ Instance Summary:\n")
        print(tabulate(summary.items(), tablefmt="fancy_grid"))

    def destroy(self):
        result = self.client.destroy_instance(self.instance_id)
        if result.get("success"):
            print(f"✅ Instance {self.instance_id} destroyed.")
        else:
            print("❌ Failed to destroy instance.")
