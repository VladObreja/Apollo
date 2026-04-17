import customtkinter as ctk
import subprocess
import threading

class HermesControlApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Project Hermes - Control Center")
        self.geometry("600x500")
        ctk.set_appearance_mode("dark")

        # UI Layout
        self.label = ctk.CTkLabel(self, text="Hermes System Operations", font=("Roboto", 20))
        self.label.pack(pady=20)

        # Global Controls
        self.btn_up = ctk.CTkButton(self, text="START ALL (Apollo + Hermes)", command=self.sys_up, fg_color="green")
        self.btn_up.pack(pady=10)

        self.btn_down = ctk.CTkButton(self, text="STOP ALL", command=self.sys_down, fg_color="red")
        self.btn_down.pack(pady=10)

        # Individual Service Toggles
        self.service_frame = ctk.CTkFrame(self)
        self.service_frame.pack(pady=20, fill="x", padx=40)

        self.add_service_control("hermes_db")
        self.add_service_control("ollama")
        self.add_service_control("apollo-agent")

        # Output Log
        self.log = ctk.CTkTextbox(self, height=150)
        self.log.pack(pady=20, fill="x", padx=20)

    def add_service_control(self, name):
        frame = ctk.CTkFrame(self.service_frame)
        frame.pack(fill="x", pady=2)
        lbl = ctk.CTkLabel(frame, text=name)
        lbl.pack(side="left", padx=10)
        btn = ctk.CTkButton(frame, text="Start", width=60, command=lambda: self.run_cmd(f"docker-compose up -d {name}"))
        btn.pack(side="right", padx=5)
        stop = ctk.CTkButton(frame, text="Stop", width=60, fg_color="gray", command=lambda: self.run_cmd(f"docker-compose stop {name}"))
        stop.pack(side="right", padx=5)

    def run_cmd(self, cmd):
        def execute():
            self.log.insert("end", f"Executing: {cmd}\n")
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                self.log.insert("end", line)
                self.log.see("end")
        threading.Thread(target=execute).start()

    def sys_up(self): self.run_cmd("apollo_up.bat")
    def sys_down(self): self.run_cmd("apollo_down.bat")

if __name__ == "__main__":
    app = HermesControlApp()
    app.mainloop()