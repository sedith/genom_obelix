from genomstack import is_localhost, LocalRunner, Config


def main():
    cfg = Config('tilthex_simu')
    runner = LocalRunner(workspace=cfg.root, setup=cfg.setup)
    delay = 0.5

    try:
        runner.run('h2 init', check=False, wait=delay)
        runner.start('genomixd', 'genomixd', wait=delay)

        for name, component in cfg.components.items():
            runner.start(name, f'{component.type}-pocolibs -f -i {name}', wait=delay)

        for name, sidecar in cfg.sidecars.items():
            runner.start(name, sidecar, wait=delay)

        print('hanging until ^C...')
        runner.hang()

    except KeyboardInterrupt:
        print('stopping')
        runner.stop_all()
    except Exception as e:
        print(f'error: {e}')
        print('killing')
        runner.kill_all()
    finally:
        runner.run('h2 end', check=False)
        runner.run(f'rm ~/.*.pid-*', check=False)


if __name__ == '__main__':
    raise SystemExit(main())
