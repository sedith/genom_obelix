import sys
from genomstack.config import Config
from genomstack.process import LocalRunner


def main():
    if len(sys.argv) != 2:
        print('usage: python3 launch_ros2.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]
    
    cfg = Config(config_arg)

    if not cfg.ros2.enabled:
        print('ros2 disabled')
        return 0

    runner = LocalRunner(workspace=str(cfg.root), setup=cfg.setup)
    try:
        for launchfile in cfg.ros2.launchfiles:
            cmds = [
                'export ROS_LOCALHOST_ONLY=0',
                f'export ROS_DOMAIN_ID={cfg.ros2.domain_id}',
                f'python3 ros2/{launchfile} {cfg.root}/ros2/config/'
            ]
            runner.start('ros2', cmds)
        runner.hang()

    except KeyboardInterrupt:
        print('stopping')
        runner.stop_all()
    except Exception as e:
        print(f'error: {e}')
        print('killing')
        runner.kill_all()


if __name__ == '__main__':
    raise SystemExit(main())
