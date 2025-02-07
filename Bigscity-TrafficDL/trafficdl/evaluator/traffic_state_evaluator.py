import os
import json
import datetime
import pandas as pd
from trafficdl.utils import ensure_dir
from trafficdl.model import loss
from logging import getLogger
from trafficdl.evaluator.abstract_evaluator import AbstractEvaluator


class TrafficStateEvaluator(AbstractEvaluator):

    def __init__(self, config):
        self.metrics = config.get('metrics', ['MAE'])  # 评估指标, 是一个 list
        self.allowed_metrics = [
            'MAE',
            'MSE',
            'RMSE',
            'MAPE',
            'masked_MAE',
            'masked_MSE',
            'masked_RMSE',
            'masked_MAPE',
            'R2',
            'EVAR',
            'RMSE_in',
            'RMSE_out']
        self.mode = config.get('evaluator_mode', 'average')  # or single
        self.config = config
        self.len_timeslots = 0
        self.result = {}  # 每一种指标的结果
        self.intermediate_result = {}  # 每一种指标每一个batch的结果
        self._check_config()
        self._logger = getLogger()

    def _check_config(self):
        if not isinstance(self.metrics, list):
            raise TypeError('Evaluator type is not list')
        for metric in self.metrics:
            if metric not in self.allowed_metrics:
                raise ValueError(
                    'the metric {} is not allowed in TrafficStateEvaluator'.format(
                        str(metric)))

    def collect(self, batch):
        """
        评估输入数据
        :param batch: (dict) 字典类型，包含两个Key:(y_true, y_pred)
        batch['y_true']: (num_samples/batch_size, timeslots, ..., feature_dim)
        batch['y_pred']: (num_samples/batch_size, timeslots, ..., feature_dim)
        :return:
        """
        if not isinstance(batch, dict):
            raise TypeError('evaluator.collect input is not a dict of user')
        y_true = batch['y_true']  # tensor
        y_pred = batch['y_pred']  # tensor
        if y_true.shape != y_pred.shape:
            raise ValueError(
                "batch['y_true'].shape is not equal to batch['y_pred'].shape")
        self.len_timeslots = y_true.shape[1]
        for i in range(1, self.len_timeslots + 1):
            for metric in self.metrics:
                if metric + '@' + str(i) not in self.intermediate_result:
                    self.intermediate_result[metric + '@' + str(i)] = []
        if self.mode.lower() == 'average':  # 前i个时间步的平均loss
            print("pred: " + str(y_pred.shape))
            print("true:" + str(y_true.shape))
            for i in range(1, self.len_timeslots + 1):
                for metric in self.metrics:
                    if metric == 'masked_MAE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mae_torch(y_pred[:, :i], y_true[:, :i], 0).item())
                    elif metric == 'masked_MSE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mse_torch(y_pred[:, :i], y_true[:, :i], 0).item())
                    elif metric == 'masked_RMSE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_rmse_torch(y_pred[:, :i], y_true[:, :i], 0).item())
                    elif metric == 'masked_MAPE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mape_torch(y_pred[:, :i], y_true[:, :i], 0).item())
                    elif metric == 'MAE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mae_torch(y_pred[:, :i], y_true[:, :i]).item())
                    elif metric == 'MSE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mse_torch(y_pred[:, :i], y_true[:, :i]).item())
                    elif metric == 'RMSE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_rmse_torch(y_pred[:, :i], y_true[:, :i]).item())
                    elif metric == 'RMSE_in':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_rmse_torch(y_pred[:, :i, 0], y_true[:, :i, 0]).item())
                    elif metric == 'RMSE_out':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_rmse_torch(y_pred[:, :i, 1], y_true[:, :i, 1]).item())
                    elif metric == 'MAPE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mape_torch(y_pred[:, :i], y_true[:, :i]).item())
                    elif metric == 'R2':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.r2_score_torch(y_pred[:, :i], y_true[:, :i]).item())
                    elif metric == 'EVAR':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.explained_variance_score_torch(y_pred[:, :i], y_true[:, :i]).item())
        elif self.mode.lower() == 'single':  # 第i个时间步的loss
            for i in range(1, self.len_timeslots + 1):
                for metric in self.metrics:
                    if metric == 'masked_MAE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mae_torch(y_pred[:, i - 1], y_true[:, i - 1], 0).item())
                    elif metric == 'masked_MSE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mse_torch(y_pred[:, i - 1], y_true[:, i - 1], 0).item())
                    elif metric == 'masked_RMSE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_rmse_torch(y_pred[:, i - 1], y_true[:, i - 1], 0).item())
                    elif metric == 'masked_MAPE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mape_torch(y_pred[:, i - 1], y_true[:, i - 1], 0).item())
                    elif metric == 'MAE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mae_torch(y_pred[:, i - 1], y_true[:, i - 1]).item())
                    elif metric == 'MSE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mse_torch(y_pred[:, i - 1], y_true[:, i - 1]).item())
                    elif metric == 'RMSE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_rmse_torch(y_pred[:, i - 1], y_true[:, i - 1]).item())
                    elif metric == 'MAPE':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.masked_mape_torch(y_pred[:, i - 1], y_true[:, i - 1]).item())
                    elif metric == 'R2':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.r2_score_torch(y_pred[:, i - 1], y_true[:, i - 1]).item())
                    elif metric == 'EVAR':
                        self.intermediate_result[metric + '@' + str(i)].append(
                            loss.explained_variance_score_torch(y_pred[:, i - 1], y_true[:, i - 1]).item())
        else:
            raise ValueError(
                'Error parameter evaluator_mode={}, please set `single` or `average`.'.format(
                    self.mode))

    def evaluate(self):
        """
        返回之前收集到的所有 batch 的评估结果
        :return:
        """
        for i in range(1, self.len_timeslots + 1):
            for metric in self.metrics:
                self.result[metric + '@' + str(i)] = sum(self.intermediate_result[metric + '@' + str(
                    i)]) / len(self.intermediate_result[metric + '@' + str(i)])
        return self.result

    def save_result(self, save_path, filename=None):
        """
        将评估结果保存到 save_path 文件夹下的 filename 文件中
        :param save_path: 保存路径
        :param filename: 保存文件名
        :return:
        """
        self.evaluate()
        ensure_dir(save_path)
        if filename is None:  # 使用时间戳
            filename = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + '_' + \
                self.config['model'] + '_' + self.config['dataset']
        self._logger.info('Evaluate result is ' + json.dumps(self.result))
        with open(os.path.join(save_path, '{}.json'.format(filename)), 'w') as f:
            json.dump(self.result, f)
        self._logger.info('Evaluate result is saved at ' +
                          os.path.join(save_path, '{}.json'.format(filename)))
        dataframe = {}
        for metric in self.metrics:
            dataframe[metric] = []
        for i in range(1, self.len_timeslots + 1):
            for metric in self.metrics:
                dataframe[metric].append(self.result[metric + '@' + str(i)])
        dataframe = pd.DataFrame(dataframe)
        dataframe.to_csv(
            os.path.join(
                save_path,
                '{}.csv'.format(filename)),
            index=False)
        self._logger.info('Evaluate result is saved at ' +
                          os.path.join(save_path, '{}.csv'.format(filename)))
        self._logger.info("\n" + str(dataframe))

    def clear(self):
        """
        清除之前收集到的 batch 的评估信息，适用于每次评估开始时进行一次清空，排除之前的评估输入的影响。
        :return:
        """
        self.result = {}
        self.intermediate_result = {}
