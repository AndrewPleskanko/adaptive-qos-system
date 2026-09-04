def predict_priority(features: dict) -> tuple:
    if features['type_code'] <= 0.5000:
        if features['retry_count'] <= 1.5000:
            return 0, 1.0000
        else:
            return 0, 0.8261
    else:
        if features['retry_count'] <= 0.5000:
            if features['recent_p99_latency'] <= 43.5478:
                if features['type_code'] <= 2.5000:
                    if features['type_code'] <= 1.5000:
                        return 2, 1.0000
                    else:
                        return 1, 1.0000
                else:
                    if features['lag_growth_rate'] <= 14.8469:
                        return 2, 0.8620
                    else:
                        return 2, 0.5339
            else:
                if features['type_code'] <= 1.5000:
                    return 2, 1.0000
                else:
                    if features['amount'] <= 916.1466:
                        return 1, 0.8125
                    else:
                        return 2, 0.6044
        else:
            if features['type_code'] <= 2.5000:
                if features['type_code'] <= 1.5000:
                    if features['recent_p99_latency'] <= 62.7419:
                        return 3, 0.9733
                    else:
                        return 2, 0.6800
                else:
                    if features['retry_count'] <= 1.5000:
                        return 1, 1.0000
                    else:
                        return 1, 0.5517
            else:
                if features['retry_count'] <= 1.5000:
                    if features['amount'] <= 2560.2736:
                        return 2, 0.9913
                    else:
                        return 3, 0.6667
                else:
                    if features['recent_p99_latency'] <= 43.6357:
                        return 3, 0.9048
                    else:
                        return 2, 0.8017
