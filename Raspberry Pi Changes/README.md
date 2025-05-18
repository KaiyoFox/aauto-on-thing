/boot/firmware/cmdline.txt add at the end of the line (NOT ON A NEW LINE):
video=HDMI-A-1:800x480@60D


/boot/firmware/config.txt

hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt=800 480 60 6 0 0 0

sudo raspi-config
Disable Screen Blanking
And enable Preformance > Read only FS once EVERYTHING is setup and works; ONLY ENABLE RO-FS ONCE THE DEVICE IS READ FOR A CAR!
