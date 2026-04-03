"""
Gllue API 客户端 - 用于从谷露系统同步数据到财务分析工具

文档参考：Gllue通用接口文档V0.7.2
"""

import requests
import hashlib
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import pandas as pd
import json
from dataclasses import dataclass


@dataclass
class GllueConfig:
    """Gllue API 配置"""
    base_url: str  # 如: https://yourcompany.gllue.com
    api_key: str   # API密钥
    private_token: Optional[str] = None  # 生成的private token
    
    def __post_init__(self):
        if not self.base_url.startswith(('http://', 'https://')):
            self.base_url = 'https://' + self.base_url
        # 去除末尾的斜杠
        self.base_url = self.base_url.rstrip('/')


class GllueAPIClient:
    """Gllue API 客户端"""
    
    def __init__(self, config: GllueConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json; charset=UTF-8',
            'Accept': 'application/json'
        })
    
    def _generate_private_token(self) -> str:
        """
        生成 Gllue Private Token
        算法：md5(api_key + timestamp)
        """
        timestamp = str(int(datetime.now().timestamp()))
        raw_string = self.config.api_key + timestamp
        token = hashlib.md5(raw_string.encode('utf-8')).hexdigest()
        return f"{token}_{timestamp}"
    
    def _get_token(self) -> str:
        """获取当前可用的 private token"""
        if self.config.private_token:
            return self.config.private_token
        return self._generate_private_token()
    
    def _build_url(self, endpoint: str, params: Dict[str, Any] = None) -> str:
        """构建请求 URL"""
        url = f"{self.config.base_url}{endpoint}"
        if params:
            query_string = urllib.parse.urlencode(params, safe=',')
            url = f"{url}?{query_string}"
        return url
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """发送 HTTP 请求"""
        # 添加 token 到参数
        if 'params' not in kwargs:
            kwargs['params'] = {}
        kwargs['params']['gllue_private_token'] = self._get_token()
        
        url = self._build_url(endpoint, kwargs.pop('params', None))
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API 请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"解析响应失败: {str(e)}")
    
    def _paginate_request(self, endpoint: str, gql: str = "", fields: str = "", 
                          page_size: int = 100, **kwargs) -> List[Dict]:
        """分页获取所有数据"""
        all_results = []
        page = 1
        
        while True:
            params = {
                'gql': gql,
                'page': page,
                'paginate_by': page_size,
                'fields': fields,
                **kwargs
            }
            
            data = self._make_request('GET', endpoint, params=params)
            
            # 获取实际数据键名（通常是对象名）
            object_name = endpoint.split('/')[-2] if '/rest/' in endpoint else 'result'
            results = data.get('result', {}).get(object_name, [])
            
            if not results:
                break
            
            all_results.extend(results)
            
            # 检查是否还有下一页
            current_page = data.get('currentpage', page)
            total_pages = data.get('totalpages', current_page)
            
            if current_page >= total_pages:
                break
            
            page += 1
            
            # 防止无限循环
            if page > 1000:
                break
        
        return all_results
    
    # ==================== 数据获取方法 ====================
    
    def get_offers(self, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None,
                   status: str = "") -> pd.DataFrame:
        """
        获取 Offer 列表
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            status: 状态筛选
        """
        # 构建查询条件
        conditions = []
        if start_date:
            conditions.append(f"signDate__gte={start_date}")
        if end_date:
            conditions.append(f"signDate__lte={end_date}")
        if status:
            conditions.append(f"_approval_status__s={status}")
        
        gql = "&".join(conditions) if conditions else ""
        
        # 请求字段 - 根据财务工具需要的字段
        fields = (
            "id,signDate,onboardDate,annualSalary,probationRange,"
            "jobsubmission__candidate__chineseName,jobsubmission__candidate__englishName,"
            "jobsubmission__joborder__jobTitle,jobsubmission__joborder__id,"
            "jobsubmission__joborder__bu____name__,jobsubmission__joborder__lineManager__user,"
            "jobsubmission__joborder__joborderuser_set__user____name__,user____name__"
        )
        
        results = self._paginate_request(
            '/rest/offersign/simple_list_with_ids',
            gql=gql,
            fields=fields,
            ordering='-signDate'
        )
        
        # 转换为 DataFrame
        df = pd.DataFrame(results)
        
        # 扁平化嵌套字段
        if not df.empty:
            df = self._flatten_offer_data(df)
        
        return df
    
    def get_onboards(self, start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取入职列表
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        """
        conditions = []
        if start_date:
            conditions.append(f"onboardDate__gte={start_date}")
        if end_date:
            conditions.append(f"onboardDate__lte={end_date}")
        
        gql = "&".join(conditions) if conditions else ""
        
        fields = (
            "id,onboardDate,probationDate,"
            "jobsubmission__candidate__chineseName,jobsubmission__candidate__englishName,"
            "jobsubmission__joborder__jobTitle,jobsubmission__joborder__id,"
            "jobsubmission__joborder__bu____name__,user____name__"
        )
        
        results = self._paginate_request(
            '/rest/onboard/simple_list_with_ids',
            gql=gql,
            fields=fields,
            ordering='-onboardDate'
        )
        
        df = pd.DataFrame(results)
        if not df.empty:
            df = self._flatten_onboard_data(df)
        
        return df
    
    def get_joborders(self, statuses: List[str] = None) -> pd.DataFrame:
        """
        获取职位列表
        
        Args:
            statuses: 职位状态列表，如 ['Live', 'Successful']
        """
        conditions = []
        if statuses:
            status_gql = ",".join(statuses)
            conditions.append(f"jobStatus__s={status_gql}")
        
        gql = "&".join(conditions) if conditions else ""
        
        fields = (
            "id,jobTitle,jobStatus,openDate,closeDate,totalCount,"
            "monthlySalary,annualSalary,employmentType,"
            "bu____name__,lineManager__user,joborderuser_set__user____name__,"
            "addedBy__user,dateAdded"
        )
        
        results = self._paginate_request(
            '/rest/joborder/simple_list_with_ids',
            gql=gql,
            fields=fields,
            ordering='-lastUpdateDate'
        )
        
        df = pd.DataFrame(results)
        if not df.empty:
            df = self._flatten_joborder_data(df)
        
        return df
    
    def get_users(self, is_active: bool = True) -> pd.DataFrame:
        """获取用户/顾问列表"""
        fields = "id,chineseName,englishName,email,mobile,isActive,dateJoined"
        
        results = self._paginate_request(
            '/rest/user/simple_list_with_ids',
            fields=fields
        )
        
        return pd.DataFrame(results)
    
    # ==================== 数据转换方法 ====================
    
    def _flatten_offer_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """扁平化 Offer 数据"""
        # 提取嵌套的候选人信息
        if 'jobsubmission__candidate__chineseName' in df.columns:
            df['候选人姓名'] = df['jobsubmission__candidate__chineseName']
        if 'jobsubmission__candidate__englishName' in df.columns:
            df['候选人英文名'] = df['jobsubmission__candidate__englishName']
        
        # 提取职位信息
        if 'jobsubmission__joborder__jobTitle' in df.columns:
            df['职位名称'] = df['jobsubmission__joborder__jobTitle']
        if 'jobsubmission__joborder__id' in df.columns:
            df['职位ID'] = df['jobsubmission__joborder__id']
        if 'jobsubmission__joborder__bu____name__' in df.columns:
            df['客户名称'] = df['jobsubmission__joborder__bu____name__']
        
        # 提取顾问信息
        if 'jobsubmission__joborder__joborderuser_set__user____name__' in df.columns:
            df['顾问'] = df['jobsubmission__joborder__joborderuser_set__user____name__']
        if 'user____name__' in df.columns:
            df['操作人'] = df['user____name__']
        
        # 重命名字段
        column_mapping = {
            'id': 'offer_id',
            'signDate': 'offer_date',
            'onboardDate': '预计入职日期',
            'annualSalary': '年薪',
            'probationRange': '试用期',
        }
        df = df.rename(columns=column_mapping)
        
        return df
    
    def _flatten_onboard_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """扁平化入职数据"""
        if 'jobsubmission__candidate__chineseName' in df.columns:
            df['候选人姓名'] = df['jobsubmission__candidate__chineseName']
        if 'jobsubmission__joborder__jobTitle' in df.columns:
            df['职位名称'] = df['jobsubmission__joborder__jobTitle']
        if 'jobsubmission__joborder__bu____name__' in df.columns:
            df['客户名称'] = df['jobsubmission__joborder__bu____name__']
        if 'user____name__' in df.columns:
            df['顾问'] = df['user____name__']
        
        column_mapping = {
            'id': 'onboard_id',
            'onboardDate': '入职日期',
            'probationDate': '试用期结束日期',
        }
        df = df.rename(columns=column_mapping)
        
        return df
    
    def _flatten_joborder_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """扁平化职位数据"""
        if 'bu____name__' in df.columns:
            df['客户名称'] = df['bu____name__']
        if 'lineManager__user' in df.columns:
            df['直线经理'] = df['lineManager__user']
        if 'joborderuser_set__user____name__' in df.columns:
            df['顾问'] = df['joborderuser_set__user____name__']
        if 'addedBy__user' in df.columns:
            df['创建人'] = df['addedBy__user']
        
        column_mapping = {
            'id': '职位ID',
            'jobTitle': '职位名称',
            'jobStatus': '职位状态',
            'openDate': '开始日期',
            'closeDate': '结束日期',
            'totalCount': '招聘人数',
            'monthlySalary': '月薪',
            'annualSalary': '年薪',
        }
        df = df.rename(columns=column_mapping)
        
        return df
    
    # ==================== 同步到财务工具的方法 ====================
    
    def sync_to_finance_analyzer(self, analyzer, start_date: str = None, 
                                  end_date: str = None) -> Dict[str, int]:
        """
        同步数据到财务分析器
        
        Args:
            analyzer: RecruitmentFinanceAnalyzer 实例
            start_date: 开始日期，默认为 1 年前
            end_date: 结束日期，默认为今天
        
        Returns:
            同步统计信息
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        stats = {
            'offers_fetched': 0,
            'onboards_fetched': 0,
            'positions_added': 0,
        }
        
        # 1. 获取 Offer 数据（作为成单数据）
        offers_df = self.get_offers(start_date=start_date, end_date=end_date)
        stats['offers_fetched'] = len(offers_df)
        
        # 2. 获取入职数据
        onboards_df = self.get_onboards(start_date=start_date, end_date=end_date)
        stats['onboards_fetched'] = len(onboards_df)
        
        # 3. 转换为财务工具的数据格式并加载
        if not offers_df.empty:
            positions_df = self._convert_to_positions_format(offers_df, onboards_df)
            analyzer.load_positions_from_dataframe(positions_df, clear_existing=True)
            stats['positions_added'] = len(positions_df)
        
        return stats
    
    def _convert_to_positions_format(self, offers_df: pd.DataFrame, 
                                      onboards_df: pd.DataFrame) -> pd.DataFrame:
        """
        将 Gllue 数据转换为财务工具需要的格式
        """
        # 基础字段映射
        result = pd.DataFrame()
        
        # 必需字段
        result['职位ID'] = offers_df.get('职位ID', '').astype(str)
        result['客户名称'] = offers_df.get('客户名称', '')
        result['职位名称'] = offers_df.get('职位名称', '')
        result['顾问'] = offers_df.get('顾问', '')
        
        # 日期字段
        result['成单日期'] = offers_df.get('offer_date', '')
        result['入职日期'] = offers_df.get('预计入职日期', '')
        
        # 财务字段
        result['年薪'] = pd.to_numeric(offers_df.get('年薪', 0), errors='coerce').fillna(0)
        result['费率%'] = 20  # 默认费率
        result['佣金总额'] = result['年薪'] * result['费率%'] / 100
        
        # 回款相关（需要从其他系统或手动补充）
        result['实际回款'] = 0
        result['回款日期'] = ''
        result['发票日期'] = ''
        
        # 上年遗留（需要从历史数据计算）
        result['上年遗留回款'] = 0
        
        # 状态标记
        result['是否成单'] = True
        
        return result


class GllueDataCache:
    """Gllue 数据缓存管理"""
    
    def __init__(self, cache_dir: str = ".gllue_cache"):
        self.cache_dir = cache_dir
        import os
        os.makedirs(cache_dir, exist_ok=True)
    
    def save(self, data: pd.DataFrame, name: str):
        """保存数据到缓存"""
        filepath = f"{self.cache_dir}/{name}_{datetime.now().strftime('%Y%m%d')}.csv"
        data.to_csv(filepath, index=False, encoding='utf-8-sig')
    
    def load(self, name: str, date: str = None) -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        filepath = f"{self.cache_dir}/{name}_{date}.csv"
        import os
        if os.path.exists(filepath):
            return pd.read_csv(filepath, encoding='utf-8-sig')
        return None
    
    def get_cache_dates(self, name: str) -> List[str]:
        """获取可用缓存日期列表"""
        import os
        import glob
        pattern = f"{self.cache_dir}/{name}_*.csv"
        files = glob.glob(pattern)
        dates = []
        for f in files:
            date_str = os.path.basename(f).replace(f"{name}_", "").replace(".csv", "")
            dates.append(date_str)
        return sorted(dates, reverse=True)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试配置
    config = GllueConfig(
        base_url="https://demo.gllue.com",
        api_key="your_api_key_here"
    )
    
    client = GllueAPIClient(config)
    
    # 测试生成 token
    print("生成的 Token:", client._generate_private_token())
    
    # 测试数据获取（需要真实环境）
    # offers = client.get_offers(start_date="2024-01-01")
    # print(f"获取到 {len(offers)} 条 Offer 数据")
    # print(offers.head())
