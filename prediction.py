import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# 加载训练集和测试集
train_data = pd.read_csv('train.csv')
test_data = pd.read_csv('test.csv')

# 假设最后一列是目标变量
X_train = train_data.iloc[:, :-1]
y_train = train_data.iloc[:, -1]
X_test = test_data.iloc[:, :-1]

# 训练模型
model = RandomForestClassifier()
model.fit(X_train, y_train)

# 进行预测
predictions = model.predict(X_test)

# 如果需要评估模型性能，可以使用以下代码
# 假设测试集包含目标变量
# y_test = test_data.iloc[:, -1]
# accuracy = accuracy_score(y_test, predictions)
# print(f'模型准确率: {accuracy:.2f}')

# 保存预测结果
predictions_df = pd.DataFrame(predictions, columns=['Predictions'])
predictions_df.to_csv('predictions.csv', index=False)