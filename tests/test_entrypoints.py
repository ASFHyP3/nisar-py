def test_nisar_py(script_runner):
    # TODO confirm correct for this project
    ret = script_runner.run(['python', '-m', 'nisar_py', '-h'])
    assert ret.success
