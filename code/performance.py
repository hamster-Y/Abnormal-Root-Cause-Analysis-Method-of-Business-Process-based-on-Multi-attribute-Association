import copy

import pm4py
import pandas as pd
import datetime
import time
import demo3
import demo4
from pm4py.objects.petri_net.importer import importer as pnml_importer
from pm4py.algo.simulation.playout.petri_net import algorithm as simulator
#导入模型
net, initial_marking, final_marking=pnml_importer.apply('Dataset/thesis.pnml')
#读取所有日志
dataframe = pd.read_csv('Dataset/thesis1.csv', sep=',')
dataframe = pm4py.format_dataframe(dataframe, case_id='case', activity_key='Activity',timestamp_key='startTime')
log = pm4py.convert_to_event_log(dataframe)  # log按照caseID顺序
# demo3.attribute((log))
aligned_traces = pm4py.conformance_diagnostics_alignments(log, net, initial_marking, final_marking)
for j in aligned_traces:
    j=demo4.reverse_result(j['alignment'])

# demo3.add(aligned_traces,log)
# demo3.lack(aligned_traces,log)
# demo3.repeat(aligned_traces)
# demo3.replace1(aligned_traces)
# demo3.replace2(aligned_traces,log)

# 添加每个事例的执行时间
for i in log:
    # start_time = i[0]['time:timestamp']  # 每个事件的第一个事例的时间
    for j in i:
        j['single_spend_time'] = int(
            (j['completeTime'] - j['startTime']).seconds + (j['completeTime'] - j['startTime']).days * 24 * 3600)
        # start_time = j['time:timestamp']


all_attribute_name = ['org:resource','fixedCost']#属性列表自定义
#
all_static_attribute = []  # 静态属性
for i in all_attribute_name:
    mark = 1
    for j in log:
        static_attribute = []
        for k in j:
            static_attribute.append(k[i])
        if len(set(static_attribute)) != 1:
            mark = 0
            break
    if mark == 1:
        all_static_attribute.append(i)

attribute_name = []  # 非静态属性
for i in all_attribute_name:
    if i not in all_static_attribute:
        attribute_name.append(i)
# attribute_name = ['RESOURCE']
# 每个案例的事件数
case_num_list = []
for i in log:
    case_num_list.append(len(i))

# 计算每种活动所需要的平均时间
activity_average_time = {}
for i in log:
    for j in i:
        if j['Activity'] not in list(activity_average_time):
            activity_average_time[j['Activity']] = [j['single_spend_time']]
        elif j['Activity'] in list(activity_average_time):
            activity_average_time[j['Activity']].append(j['single_spend_time'])
for i in list(activity_average_time):
    sum = 0
    for j in activity_average_time[i]:
        sum = sum + j
    activity_average_time[i] = sum / len(activity_average_time[i])

# 判断案例是否超时
overtime_list = []  # 存放所有超时事件，方便整体相关性计算,去重
all_list = []  # 存放各个案例的异常活动
super_all_list = []  # 存放各个案例的异常活动,不去重
log_index = 0  # 遍历案例的下标
case_time = {'超时': [], '未超时': []}  # 案例超时与不超时划分
# all_overtime_list = []  # 存放所有超时事件，方便整体相关性计算,不去重

while log_index < len(log):  # 逐个案例分析是否超时、案例中各个事件的异常类型
    actual_time = 0  # 实际时间
    reasonable_time = 0  # 合理时间
    activity_index = 0
    for j in aligned_traces[log_index]:  # 统计合理时间
        if j[0] == j[1]:  # 行为合规
            reasonable_time = reasonable_time + log[log_index][activity_index]['single_spend_time']
        if j[0] != '>>':  # 遍历事件下标
            activity_index += 1
    for j in log[log_index]:  # 统计实际时间
        actual_time = actual_time + activity_average_time[j['Activity']]
    if actual_time <= reasonable_time:  # 记录案例是否超时
        case_time['未超时'].append(log_index)
    else:
        case_time['超时'].append(log_index)
    event_type = {}  # 事件类型
    for k in aligned_traces[log_index]['alignment']:  # 找到案例中的添加、返工、正常事件
        if k[0] == k[1]:  # 合规
            if k[0] not in list(event_type):  # 第一次执行
                event_type[k[0]] = ['正常', 1]
            else:
                event_type[k[0]][1] += 1  # 第n执行
        elif k[0] == '>>':
            pass
        elif k[1] == '>>':  # 添加
            if k[0] not in list(event_type):  # 第一次执行
                event_type[k[0]] = ['添加', 1]
            elif k[0] in list(event_type) and event_type[k[0]] == '添加':  # 第n次执行，且该活动为添加活动
                over_sum = event_type[k[0]][1]
                event_type[k[0]] = ['添加', over_sum + 1]
            elif k[0] in list(event_type) and event_type[k[0]][1] > 0:
                over_sum = event_type[k[0]][1]
                event_type[k[0]] = ['返工', over_sum + 1]
    exception_type = {'事件超时': [], '返工': [], '添加': []}
    all_exception_type = {'事件超时': [], '返工': [], '添加': []}  # 不去重，便于计算单个案例的元组
    event_index = 0  # 遍历的事件下标
    rework_times = {}
    for k in aligned_traces[log_index]['alignment']:  # 寻找添加、返工、事件超时
        if k[0] != '>>':  # 日志中存在
            if event_type[k[0]][0] != '添加' and event_type[k[0]][0] != '返工' and activity_average_time[k[0]] < \
                    log[log_index][event_index][
                        'single_spend_time']:  # 事件超时
                overtime_list.append(log[log_index][event_index])  # 将超时事件添加进超时事件列表
                event_mark = 1  # 用来标记同一超时活动的属性值是否相同
                event_exist = 0  # 用来标记是否存在该活动
                for k1 in exception_type['事件超时']:  # 查看是否有其相同的活动
                    if k1['Activity'] == log[log_index][event_index]['Activity']:  # 存在与其相同的活动
                        event_exist = 1
                        for attribute_value in attribute_name:  # 查看同一超时活动的属性值是否相同
                            if k1[attribute_value] != log[log_index][event_index][attribute_value]:  # 存在属性值不同的情况
                                event_mark = 0
                if event_exist == 0:  # 该超时活动第一执行
                    exception_type['事件超时'].append(log[log_index][event_index])
                if event_exist == 1 and event_mark == 0:  # 该超时活动第n次执行，但属性值有差异，则添加该事件
                    exception_type['事件超时'].append(log[log_index][event_index])
                all_exception_type['事件超时'].append(log[log_index][event_index])
            if event_type[k[0]][0] == '返工' and event_type[k[0]][1] > 1:  # 该活动参与其返工,只统计前n-1次的属性值
                if k[0] not in list(rework_times):
                    rework_times[k[0]] = 1
                else:
                    rework_times[k[0]] += 1
                if rework_times[k[0]] != event_type[k[0]][1]:
                    overtime_list.append(log[log_index][event_index])  # 将返工异常除了最后一次的事件添加进超时事件列表
                    all_exception_type['返工'].append(log[log_index][event_index])
                    event_mark = 1  # 用来标记返工活动的属性值是否相同
                    event_exist = 0  # 用来标记是否存在该活动
                    for k1 in exception_type['返工']:  # 查看是否有其相同的活动
                        if k1['Activity'] == log[log_index][event_index]['Activity']:  # 存在与其相同的活动
                            event_exist = 1
                            for attribute_value in attribute_name:  # 查看返工活动的属性值是否相同
                                if k1[attribute_value] != log[log_index][event_index][
                                    attribute_value]:  # 存在属性值不同的情况
                                    event_mark = 0
                    if event_exist == 0:  # 该返工活动第一执行
                        exception_type['返工'].append(log[log_index][event_index])
                    if event_exist == 1 and event_mark == 0:  # 返工活动第n次执行，但属性值有差异，则添加该事件
                        exception_type['返工'].append(log[log_index][event_index])
            if event_type[k[0]][0] == '添加':  # 该活动额外执行
                overtime_list.append(log[log_index][event_index])  # 将额外进行的事件添加到超时事件列表
                event_mark = 1  # 用来标记添加活动的属性值是否相同
                event_exist = 0  # 用来标记是否存在该活动
                for k1 in exception_type['添加']:  # 查看是否有其相同的活动
                    if k1['Activity'] == log[log_index][event_index]['Activity']:  # 存在与其相同的活动
                        event_exist = 1
                        for attribute_value in attribute_name:  # 查看添加活动的属性值是否相同
                            if k1[attribute_value] != log[log_index][event_index][attribute_value]:  # 存在属性值不同的情况
                                event_mark = 0
                if event_exist == 0:  # 该添加活动第一执行
                    exception_type['添加'].append(log[log_index][event_index])
                if event_exist == 1 and event_mark == 0:  # 添加活动第n次执行，但属性值有差异，则添加该事件
                    exception_type['添加'].append(log[log_index][event_index])
                all_exception_type['添加'].append(log[log_index][event_index])
            event_index += 1
    all_list.append(exception_type)  # 每个案例的事件超时、返工、添加为一个字典存在all列表中
    super_all_list.append(all_exception_type)  # 每个案例的事件超时、返工、添加为一个字典存在all列表中
    log_index += 1

# 统计静态属性的合规与不合规属性值
if len(all_static_attribute)>0:
    print('静态属性及其区间')
    for i in all_static_attribute:
        right_value_dic = {}
        for j in case_time['未超时']:
            if log[j][0][i] not in list(right_value_dic):
                right_value_dic[log[j][0][i]] = 1
            else:
                right_value_dic[log[j][0][i]] += 1

        wrong_value_dic = {}
        for j in case_time['超时']:
            if log[j][0][i] not in list(wrong_value_dic):
                wrong_value_dic[log[j][0][i]] = 1
            else:
                wrong_value_dic[log[j][0][i]] += 1
        right_value_list = []
        wrong_value_list = []
        for j in list(right_value_dic):
            mark = 1
            for k in list(wrong_value_dic):
                if j == k:
                    mark = 0
                    break
            if mark == 1:
                right_value_list.append(j)
            else:
                print(right_value_dic[j])
                print(wrong_value_dic[j])
                if right_value_dic[j]/(right_value_dic[j]+wrong_value_dic[j])>=1:
                    right_value_list.append(j)
                    del wrong_value_dic[j]
        print(i,end=':')
        print('合法属性值区间',end=':')
        print(right_value_list,end='   非法属性值区间')
        print(list(wrong_value_dic))
else:
    print('不存在静态属性')
type_sequence = {'事件超时': 0, '返工': 0, '添加': 0}
all_attribute_list = []
all_tuple_list = []  # 存储所有元组
all_case_tuple_list = []
all_event_impace_list = []
x = 0
y_all = []
case_list = {}
for i in all_list:  # i为案例
    case_tuple = []  # 存放一个案例的元组
    event_impace_list = []  # 案例中的事件属性对
    for j in list(type_sequence):  # j为事件超时、返工、添加key
        for k in i[j]:  # 案例的三个key的value分别遍历，k为事件
            a_tuple_list = []  # 存放单个事件的所有元组
            for l in attribute_name:  # l为属性
                a = [j, k['Activity'], l, k[l], 0, 0, 0, 0, x]  # 超时类别,活动名,属性,属性值,影响案例数,整体相关性,案例的影响案例数,案例相关性,caseID
                # 整体
                # 影响案例数
                for j1 in all_list:  # j1为案例
                    for k1 in j1[j]:  # k1为事件
                        if k1[l] == k[l] and k1['Activity'] == k['Activity']:
                            a[4] += 1
                # 相关性，所有案例的超时总时间，不去重
                for j2 in overtime_list:  # j2为超时事件
                    if j2[l] == k[l]:  # 遍历看该属性值参与的超时事件
                        a[5] = a[5] + j2['single_spend_time']
                # 案例
                # 影响案例数--->执行次数
                for j4 in super_all_list[x][j]:
                    if j4['Activity'] == k['Activity'] and j4[l] == k[l]:
                        a[6] += 1
                # 相关性,一个案例中的所有超时，不去重，a返工多次的总时间
                for j5 in list(type_sequence):
                    for k3 in super_all_list[x][j5]:
                        if k3[l] == k[l]:
                            a[7] = a[7] + k3['single_spend_time']
                all_tuple_list.append(a)
                case_tuple.append(a)
                a_tuple_list.append(a)
            event_impace_list.append(a_tuple_list)  # 单个事件的属性对
    all_case_tuple_list.append(case_tuple)
    all_event_impace_list.append(event_impace_list)
    x += 1
# print(all_tuple_list)
# 对整体的属性排序
attribute_dic = {}
for i in attribute_name:
    attribute_dic[i] = 0
for i in all_tuple_list:
    if i[4] > attribute_dic[i[2]]:
        attribute_dic[i[2]] = i[4]
print(attribute_dic)
attribute_sequence = sorted(attribute_dic, key=attribute_dic.get, reverse=True)  # ['Costs', 'Resource']

# 对事件超时、返工、添加类别排序
for i in all_tuple_list:
    if i[0] == '事件超时':
        type_sequence['事件超时'] += 1
    elif i[0] == '返工':
        type_sequence['返工'] += 1
    elif i[0] == '添加':
        type_sequence['添加'] += 1
type_sequence_reverse = sorted(type_sequence, key=type_sequence.get, reverse=True)  # ['事件超时', '添加', '返工']
type_sequence_reverse_dic = {'事件超时': [], '返工': [], '添加': []}  # 收纳大类下的元组
for i in all_tuple_list:  # 所有元组按照大类归类,['事件超时':[], '添加': [], '返工': []]
    if i[8] in case_time['超时']:  # 只收集超时案例中的元组并排序
        type_sequence_reverse_dic[i[0]].append(i)
# print(type_sequence_reverse_dic)

if len(attribute_name)>0:
    print('***************************************流程超时的原因序列************************************')
    print()
    print('         异常点                             属性             不合法属性值')
    for i in type_sequence_reverse:

        activity_sum_dic = {}
        for j in type_sequence_reverse_dic[i]:
            if j[1] + j[0] not in list(activity_sum_dic):
                activity_sum_dic[j[1] + j[0]] = 0
            else:
                activity_sum_dic[j[1] + j[0]] += 1
        activity_sum_sequence_reverse = sorted(activity_sum_dic, key=activity_sum_dic.get, reverse=True)  # 大类中的异常活动排序
        for k in activity_sum_sequence_reverse:
            print('------------------------------------------------------------------------------------------')
            print(k, end='')
            x = 0
            flag = 1
            for l in attribute_sequence:
                if flag == 1:
                    x = 0
                    while x < 40 - len(k):
                        print(' ', end='')
                        x += 1
                    flag = 0
                else:
                    x = 0
                    while x < 40:
                        print(' ', end='')
                        x += 1
                print(l, end='')
                x = 0
                while x < 20 - len(l):
                    print(' ', end='')
                    x += 1
                similar_event = []
                for q in all_tuple_list:
                    if q[1] + q[0] == k and q[2] == l:
                        similar_event.append(q)
                # 此处需要对similar_event做去重处理
                similar_event2 = []
                for q in similar_event:
                    mark = 1
                    for q2 in similar_event2:
                        if q[0:6] == q2[0:6]:
                            mark = 0
                    if mark == 1:
                        similar_event2.append(q)
                similar_event_sequence = sorted(similar_event2, key=lambda x: x[5], reverse=True)
                x = 0
                while x < len(similar_event_sequence):
                    if x != len(similar_event_sequence) - 1:
                        print(similar_event_sequence[x][3], end='、')
                    else:
                        print(similar_event_sequence[x][3])
                    x += 1
                # for p in similar_event_sequence:
                #     print(p[0:6])

#     print()
#     print()
#     print('***************************************案例超时的原因序列************************************')
#     print()
#     print('         异常点                             属性             不合法属性值')
#     # 对案例分析
#     case_index = 0
#     while case_index < len(all_list):
#         if case_index in case_time['超时']:
#             print('------------------------------------------------------------------------------------------')
#             # 输出案例编号
#             print('CaseID:', end='')
#             print(log[case_index][0]['case'])
#             case_type_sequence_dic = {'事件超时': [0, type_sequence['事件超时']], '返工': [0, type_sequence['返工']],
#                                       '添加': [0, type_sequence['添加']]}  # 对案例的大类排序:比较案例级别，若相同再比较流程级别
#             for i in all_case_tuple_list[case_index]:
#                 case_type_sequence_dic[i[0]][0] += 1
#             case_type_sequence = sorted(case_type_sequence_dic.keys(),
#                                         key=lambda x: (case_type_sequence_dic[x][0], case_type_sequence_dic[x][1]),
#                                         reverse=True)  # 大类排序列表
#             case_mark = 1
#             for z in aligned_traces[case_index]['alignment']:
#                 if z[0] == z[1] or (z[0] == '>>' and z[1] != '>>'):
#                     pass
#                 else:
#                     case_mark = 0
#                     break
#             if case_mark == 1 and case_type_sequence_dic['事件超时'][0]==0 and case_type_sequence_dic['返工'][0]==0 and case_type_sequence_dic['添加'][0]==0:
#                 print('案例中仅存在事件缺失行为异常，暂不分析')
#             else:
#                 print()
#             case_attribute_dic = {}  # 对案例中的属性排序
#             for i in attribute_name:
#                 case_attribute_dic[i] = [0]
#                 case_attribute_dic[i].append(attribute_dic[i])
#             for j in all_case_tuple_list[case_index]:
#                 if j[6] > case_attribute_dic[j[2]][0]:
#                     case_attribute_dic[j[2]][0] = j[6]
#
#             case_attribute_sequence = sorted(case_attribute_dic.keys(),
#                                              key=lambda x: (case_attribute_dic[x][0], case_attribute_dic[x][1]),
#                                              reverse=True)  # 案例的属性排序列表
#
#             case_type_sequence_reverse_dic = {'事件超时': [], '返工': [], '添加': []}  # 收纳大类下的元组
#             for j in all_case_tuple_list[case_index]:  # 各个大类下的元组
#                 case_type_sequence_reverse_dic[j[0]].append(j)
#             for j in case_type_sequence:  # 大类排序
#                 case_activity_sum_dic = {}
#                 for k in case_type_sequence_reverse_dic[j]:  # 遍历大类中的元组
#                     if k[1] + k[0] not in list(case_activity_sum_dic):
#                         case_activity_sum_dic[k[1] + k[0]] = 1
#                     else:
#                         case_activity_sum_dic[k[1] + k[0]] += 1
#                 case_activity_sum_sequence_reverse = sorted(case_activity_sum_dic, key=case_activity_sum_dic.get,
#                                                             reverse=True)  # 大类中的异常活动排序
#
#                 for l in case_activity_sum_sequence_reverse:
#                     print(l, end='')
#                     flag = 1
#                     for l1 in case_attribute_sequence:
#                         if flag == 1:
#                             x = 0
#                             while x < 40 - len(l):
#                                 print(' ', end='')
#                                 x += 1
#                             flag = 0
#                         else:
#                             x = 0
#                             while x < 40:
#                                 print(' ', end='')
#                                 x += 1
#                         print(l1, end='')
#                         x = 0
#                         while x < 20 - len(l1):
#                             print(' ', end='')
#                             x += 1
#                         b = []
#                         for l2 in all_case_tuple_list[case_index]:
#                             if l2[1] + l2[0] == l and l2[2] == l1:
#                                 b.append(l2)
#                         b_list = sorted(b, key=lambda x: (-x[6], -x[4]))
#                         x = 0
#                         while x < len(b_list):
#                             if x != len(b_list) - 1:
#                                 print(b_list[x][3], end='、')
#                             else:
#                                 print(b_list[x][3])
#                             x += 1
#                         # for l3 in b_list:
#                         #     print(l3)
#         case_index += 1
# print(all_tuple_list)
# b1={'R_31_1G':[],'R_21_1F':[],'R_14_1D':[],'R_45_2A':[],'R_33_1L':[],'R_48_2D':[],'R_13_1C':[],'R_47_2C':[],'R_46_2B':[]}
# a1=[]
# for i in all_tuple_list:
#     for j in list(b1):
#         if i[0]=='事件超时' and i[1]=='Remove trocar':
#             b1[i[3]].append(i[5])
# for i in list(b1):
#     if b1[i]!=[]:
#         b1[i]=max(b1[i])
#     else:
#         b1[i]=0
# print(b1)
# b2={'R_21_1F':[],'R_48_2D':[],'R_33_1L':[],'R_32_1H':[],'R_13_1C':[],'R_47_2C':[],'R_46_2B':[]}
# for i in all_tuple_list:
#     for j in list(b2):
#         if i[0]=='事件超时' and i[1]=='Clean puncture area':
#             b2[i[3]].append(i[5])
# print(b2)
# b3={'R_31_1G':[],'R_21_1F':[],'R_14_1D':[],'R_45_2A':[],'R_48_2D':[],'R_33_1L':[],'R_47_2C':[],'R_13_1C':[],'R_32_1H':[],'R_46_2B':[]}
# for i in all_tuple_list:
#     for j in list(b3):
#         if i[0]=='事件超时' and i[1]=='Guidewire install':
#             b3[i[3]].append(i[5])
# print(b3)
# a1=0
# for i in all_tuple_list:
#     if i[0]=='事件超时' and i[1]=='Remove trocar':
#         a1+=1
# print(a1)
# a2=0
# for i in all_tuple_list:
#     if i[0]=='事件超时' and i[1]=='Clean puncture area':
#         a2+=1
# print(a2)
# a3=0
# for i in all_tuple_list:
#     if i[0]=='事件超时' and i[1]=='Guidewire install':
#         a3+=1
# print(a3)