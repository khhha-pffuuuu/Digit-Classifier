import pickle
from app.app import launch_app


def main():
    model = pickle.load(open('model/xgb_model.pkl', 'rb'))
    launch_app(model)


if __name__ == '__main__':
    main()
