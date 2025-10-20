from .vast_manager import VastManager

def main():
    vm = VastManager()
    instances = {}

    while True:
        print("\n📋 Vast CLI Menu")
        print("1. Query + Display Offers")
        print("2. Launch Instance")
        print("3. Show Instance Info")
        print("4. Destroy Instance")
        print("5. Exit")

        choice = input("Select an option: ").strip()

        if choice == "1":
            vm.query_offers()
            vm.display_offers()

        elif choice == "2":
            offers = vm.display_offers()
            if not offers:
                continue
            try:
                index = int(input("Select offer index to launch (-1 to exit): "))
                if index == -1:
                    continue
                offer = offers[index]
                result = vm.create_instance(offer["id"])
                inst_id = result["new_contract"]
                instances[inst_id] = offer
                print(f"🚀 Instance launched with ID: {inst_id}")
            except (ValueError, IndexError, KeyError) as e:
                print(f"❌ Invalid selection: {e}")

        elif choice == "3":
            if not instances:
                print("ℹ️ No tracked instances.")
                continue
            print("\n🖥️ Launched Instances:")
            for i, inst_id in enumerate(instances):
                print(f"{i}. ID: {inst_id}, GPU: {instances[inst_id]['gpu_name']}, Region: {instances[inst_id]['geolocation']}")
            try:
                index = int(input("Select instance index to view: "))
                inst_id = list(instances.keys())[index]
                vm.show_instance(inst_id)
            except (ValueError, IndexError):
                print("❌ Invalid selection.")

        elif choice == "4":
            if not instances:
                print("ℹ️ No tracked instances.")
                continue
            print("\n🗑️ Launched Instances:")
            for i, inst_id in enumerate(instances):
                print(f"{i}. ID: {inst_id}, GPU: {instances[inst_id]['gpu_name']}, Region: {instances[inst_id]['geolocation']}")
            try:
                index = int(input("Select instance index to destroy: "))
                inst_id = list(instances.keys())[index]
                confirm = input(f"Are you sure you want to destroy instance {inst_id}? Type 'yes' to confirm: ").strip().lower()
                if confirm == "yes":
                    vm.destroy_instance(inst_id)
                    del instances[inst_id]
                    print("✅ Instance destroyed.")
            except (ValueError, IndexError):
                print("❌ Invalid selection.")

        elif choice == "5":
            print("👋 Exiting CLI.")
            break

        else:
            print("❌ Invalid option.")

if __name__ == "__main__":
    main()
