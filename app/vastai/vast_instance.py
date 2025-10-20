from tabulate import tabulate

class VastInstance:
    def __init__(self, instance_id, offer_id, client):
        self.instance_id = instance_id
        self.offer_id = offer_id
        self.client = client

    def show(self):
        data = self.client.show_instance(self.instance_id).get("instances", {})
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
            "SSH Host": data.get("ssh_host"),
            "SSH Port": data.get("ssh_port"),
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
