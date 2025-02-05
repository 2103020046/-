# views.py
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Order, Item
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm

# 配置日志记录
logger = logging.getLogger(__name__)


@csrf_exempt
def create_order(request):
    if request.method == 'POST':
        try:
            # 打印接收到的表单数据
            logger.info(f"Received POST data: {request.POST}")

            # 解析表单数据
            order_data = {
                'order_number': request.POST.get('orderNo'),  # 运单号
                'sender': request.POST.get('senderName', ''),  # 发货人
                'sender_phone': request.POST.get('senderPhone', ''),  # 发货人手机号
                'sender_address': request.POST.get('senderAddress', ''),  # 发货详细地址
                'product_code': request.POST.get('productCode', ''),  # 货号
                'receiver': request.POST.get('receiverName', ''),  # 收货方
                'receiver_phone': request.POST.get('receiverPhone', ''),  # 收货人手机号
                'receiver_address': request.POST.get('receiverAddress', ''),  # 收货详细地址
                'total_freight': request.POST.get('totalFee', 0),  # 总费用
                'payment_method': request.POST.get('paymentMethod', ''),  # 支付方式
                'return_requirement': request.POST.get('returnRequirement', ''),  # 回单要求
                'other_expenses': request.POST.get('otherExpenses', 0),  # 其他支出
                'expense_details': request.POST.get('feeDescription', ''),  # 费用说明
                'carrier': request.POST.get('carrier', ''),  # 承运商
                'carrier_address': request.POST.get('carrierAddress', ''),  # 到站地址
                'arrival_address': request.POST.get('arrivalAddress', ''),  # 发站地址
                'departure_station_phone': request.POST.get('departureStationPhone', None),  # 发站查询电话
                'arrival_station_phone': request.POST.get('arrivalStationPhone', ''),  # 到站查询电话
                'customer_order_no': request.POST.get('customerOrderNo', ''),  # 客户单号
                'date': request.POST.get('date'),  # 日期
                'departure_station': request.POST.get('departureStation'),  # 发站
                'arrival_station': request.POST.get('arrivalStation'),  # 到站
                'transport_method': request.POST.get('transportMethod'),  # 运输方式
                'delivery_method': request.POST.get('deliveryMethod'),  # 交货方式
                'sender_sign': request.POST.get('senderSign'),  # 发货人签名
                'receiver_sign': request.POST.get('receiverSign'),  # 收货人签名
                'id_card': request.POST.get('idCard'),  # 身份证号
                'order_maker': request.POST.get('orderMaker')  # 制单人
            }

            # 确保所有必需字段都有值
            required_fields = ['order_number', 'sender', 'sender_phone', 'sender_address', 'receiver', 'receiver_phone',
                               'receiver_address']
            for field in required_fields:
                if not order_data[field]:
                    return JsonResponse({'status': 'error', 'message': f'Missing required field: {field}'}, status=400)

            # 创建Order实例
            order = Order.objects.create(**{k: v for k, v in order_data.items() if v is not None})

            # 处理商品数据
            items = []
            i = 0
            while True:
                try:
                    item_key = f'items[{i}][productName]'
                    if item_key not in request.POST:  # 检查是否存在该键
                        break
                    item_data = {
                        'order_id': order.id,
                        'item_name': request.POST[f'items[{i}][productName]'],  # 品名
                        'package_type': request.POST[f'items[{i}][packageType]'],  # 包装
                        'quantity': int(request.POST[f'items[{i}][quantity]']),  # 件数
                        'weight': float(request.POST[f'items[{i}][weight]']),  # 重量
                        'volume': float(request.POST[f'items[{i}][volume]']),  # 体积
                        'delivery_charge': request.POST.get('deliveryCharge', 0),  # 送（提）货费
                        'insurance_fee': request.POST.get('insuranceFee', 0),  # 保险费
                        'packaging_fee': request.POST.get('packagingFee', 0),  # 包装费
                        'goods_value': request.POST.get('goodsValue', 0),  # 货物价值
                        'remarks': request.POST.get('remarks', 0),  # 备注
                        'freight': float(request.POST[f'items[{i}][freight]'])  # 运费
                    }
                    items.append(Item.objects.create(**item_data))
                    i += 1
                except (KeyError, ValueError) as e:
                    return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
                except IndexError:
                    break

                # 返回包含 orderId 的 JSON 响应
                return JsonResponse({
                    'status': 'success',
                    'message': 'Order created successfully',
                    'orderId': order.id  # 添加 orderId 到响应中
                })

            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Unexpected error creating order: {str(e)}", exc_info=True)
            return JsonResponse(
                {'status': 'error', 'message': f' {str(e)},An unexpected error occurred. Please try again later.'},
                status=500)


def index(request):
    return render(request, 'index.html')


def custom_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)

    return wrapper


@custom_login_required
@login_required
def orders(request):
    return render(request, 'order.html')


@custom_login_required
@login_required
def order_history(request):
    # 获取所有订单数据
    orders = Order.objects.all()

    # 分页设置
    paginator = Paginator(orders, 10)  # 每页显示10条数据
    page = request.GET.get('page')  # 获取当前页码

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        # 如果页码不是整数，则返回第一页
        orders_page = paginator.page(1)
    except EmptyPage:
        # 如果页码超出范围，则返回最后一页
        orders_page = paginator.page(paginator.num_pages)

    return render(request, 'order_history.html', {'orders': orders_page})


@csrf_exempt
def get_order_detail(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        items = order.items.all()  # 获取所有关联的商品信息
        items_data = [{
            'item_name': item.item_name,
            'package_type': item.package_type,
            'quantity': item.quantity,
            'weight': str(item.weight),  # 转换为字符串以避免 JSON 序列化问题
            'volume': str(item.volume),
            'delivery_charge': str(item.delivery_charge),
            'insurance_fee': str(item.insurance_fee),
            'packaging_fee': str(item.packaging_fee),
            'goods_value': str(item.goods_value),
            'remarks': str(item.remarks),
            'freight': str(item.freight),
        } for item in items]

        return JsonResponse({
            'order_number': order.order_number,
            'sender': order.sender,
            'sender_phone': order.sender_phone,
            'sender_address': order.sender_address,
            'product_code': order.product_code,
            'receiver': order.receiver,
            'receiver_phone': order.receiver_phone,
            'receiver_address': order.receiver_address,
            'total_freight': str(order.total_freight),  # 转换为字符串
            'payment_method': order.payment_method,
            'other_expenses': str(order.other_expenses),  # 转换为字符串
            'expense_details': order.expense_details,
            'carrier': order.carrier,
            'carrier_address': order.carrier_address,
            'arrival_address': order.arrival_address,
            'return_requirement': order.return_requirement,
            'departure_station_phone': order.departure_station_phone,
            'arrival_station_phone': order.arrival_station_phone,
            'customer_order_no': order.customer_order_no,
            'date': order.date,
            'departure_station': order.departure_station,
            'arrival_station': order.arrival_station,
            'transport_method': order.transport_method,
            'delivery_method': order.delivery_method,
            'sender_sign': order.sender_sign,
            'receiver_sign': order.receiver_sign,
            'id_card': order.id_card,
            'order_maker': order.order_maker,
            'items': items_data,  # 返回商品信息
        })
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)


def edit_order(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items'), id=order_id)

    if request.method == 'POST':
        # 更新订单基本信息
        order.sender = request.POST.get('senderName')
        order.receiver = request.POST.get('receiverName')
        # 更新其他字段（按实际字段补充）
        order.save()

        # 更新商品项
        order.items.all().delete()  # 删除旧商品项
        index = 0
        while True:
            product_name = request.POST.get(f'items[{index}][productName]')
            if not product_name:
                break
            Item.objects.create(
                order=order,
                item_name=product_name,
                package_type=request.POST.get(f'items[{index}][packageType]'),
                quantity=request.POST.get(f'items[{index}][quantity]'),
                weight=request.POST.get(f'items[{index}][weight]'),
                volume=request.POST.get(f'items[{index}][volume]'),
                freight=request.POST.get(f'items[{index}][freight]'),
            )
            index += 1
        return redirect('order_history')

    return render(request, 'edit_order.html', {'order': order})


def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    return JsonResponse({'status': 'success'})


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            messages.error(request, '用户名或密码错误，请重试。')
    return render(request, 'login.html')


def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            messages.error(request, '两次输入的密码不一致，请重试。')
        else:
            user = User.objects.create_user(username=username, password=password1)
            login(request, user)  # 自动登录新用户
            messages.success(request, '注册成功！')
            return redirect('/')
    return render(request, 'register.html')


def logout_view(request):
    logout(request)
    return redirect('/')
