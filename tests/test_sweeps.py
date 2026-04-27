from teleportdim.sweeps import fixed_n_dimensions, fixed_n_sweep_configs


def test_fixed_n_dimensions_controlled_groups() -> None:
    assert fixed_n_dimensions(1) == [2]
    assert fixed_n_dimensions(2) == [2, 3, 4]
    assert fixed_n_dimensions(3) == [4, 5, 6, 7, 8]


def test_fixed_n_sweep_configs_builds_expected_dimensions() -> None:
    configs = fixed_n_sweep_configs([2], delay_dt_values=[0, 64])
    assert [cfg.dimension for cfg in configs] == [2, 3, 4]
    assert all(list(cfg.delay_dt_values) == [0, 64] for cfg in configs)
