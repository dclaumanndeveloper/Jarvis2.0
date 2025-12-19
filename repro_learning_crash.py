try:
    print("Attempting to import LearningModule...")
    from learning_engine import LearningModule
    print("Import successful. Attempting to initialize LearningModule...")
    lm = LearningModule()
    print("Initialization successful.")
except Exception as e:
    import traceback
    print("Caught exception:")
    traceback.print_exc()
except BaseException as e:
    # Catching BaseException to catch everything
    import traceback
    print("Caught BaseException:")
    traceback.print_exc()
except:
    import traceback
    print("Caught something not inheriting from BaseException?!")
    traceback.print_exc()
