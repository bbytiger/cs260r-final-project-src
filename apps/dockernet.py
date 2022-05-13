import os
import docker
import multiprocessing as mpc

# docker with networking

def send(port: int, script: str, remote_host: str, 
        workdir: str, dockercli, container):
    exec_id = dockercli.exec_create(container.id, 
            f"python {script} {remote_host} {port}", workdir=workdir)
    execo = client.api.exec_start(exec_id)
    print(f"send output {execo}")

def recv(port: int, script: str, workdir: str, 
        dockercli, container):
    exec_id = dockercli.exec_create(container.id, 
            f"python {script} {port}", workdir=workdir)
    execo = client.api.exec_start(exec_id)
    print(f"recv output {execo}")

if __name__ == "__main__":
    # config
    port = 8001
    read_script = "readnet.py"
    write_script = "writenet.py"
    scripts_dir = "./dockerscripts"
    remote_volume = "/scripts"
    network_name = 'dockernet'
    image_name = 'python'

    # init client
    client = docker.from_env()

    # check if image exists, pull if not
    try:
        client.api.inspect_image(image_name)    
    except Exception as e:
        client.images.pull(image_name)

    # setup docker network
    nw = client.api.create_network(network_name)
    nw_config = client.api.create_networking_config({
        network_name: client.api.create_endpoint_config()
    })

    # create containers
    abs_scripts_dir = os.path.abspath(scripts_dir)
    bind = f"{abs_scripts_dir}:{remote_volume}"
    host_config = client.api.create_host_config(binds=[bind]) 
    send_container_id = client.api.create_container(image_name, detach=True,
            tty=True, networking_config=nw_config, volumes=[remote_volume], 
            host_config=host_config)
    recv_container_id = client.api.create_container(image_name, detach=True,
            tty=True, networking_config=nw_config, volumes=[remote_volume], 
            host_config=host_config) 

    # get containers and start
    send_container = client.containers.get(send_container_id)
    recv_container = client.containers.get(recv_container_id)
    send_container.start()
    recv_container.start()
    
    # get remote host
    container_info = client.api.inspect_container(recv_container_id["Id"])
    nw_info = container_info["NetworkSettings"]["Networks"]
    remote_host = nw_info[network_name]["IPAddress"]

    print("remote_host", remote_host)

    sendproc = mpc.Process(target=send, args=(port, write_script, remote_host, 
        remote_volume, client.api, send_container,))
    recvproc = mpc.Process(target=recv, args=(port, read_script, remote_volume, 
        client.api, recv_container,))

    # start and join processes
    sendproc.start()
    recvproc.start()
    sendproc.join()
    recvproc.join()
    
    # remove network and clean containers
    send_container.stop()
    recv_container.stop() 
    client.api.remove_container(send_container_id)
    client.api.remove_container(recv_container_id)
    client.api.remove_network(nw["Id"])
