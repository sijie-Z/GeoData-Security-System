class BCH:
    """BCH纠错码实现"""
    def __init__(self, polynomial, t):
        self.polynomial = polynomial
        self.t = t  # 纠错能力
    
    def encode(self, data):
        """编码数据，添加纠错码"""
        # 简化的BCH编码实现
        # 在实际应用中应使用完整的BCH编码算法
        return data + [0] * (self.t * 2)
    
    def decode(self, data):
        """解码数据，尝试纠正错误"""
        # 简化的BCH解码实现
        # 在实际应用中应使用完整的BCH解码算法
        return True, data[:len(data) - self.t * 2]