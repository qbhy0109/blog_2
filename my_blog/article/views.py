from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView
from comment.models import Comment

from .forms import ArticlePostForm
from .models import ArticlePost
from .models import ArticleColumn

import markdown


# 视图函数
def article_list(request):
    search = request.GET.get('search')
    order = request.GET.get('order')
    column = request.GET.get('column')
    tag = request.GET.get('tag')

    # 初始化查询集
    articlelist = ArticlePost.objects.all()

    # 搜索查询集
    if search:
        articlelist = articlelist.filter(Q(title__icontains=search) | Q(body__icontains=search))
    else:
        # 将 search 参数重置为空
        search = ""

    # 栏目查询集
    if column is not None and column.isdigit():
        articlelist = articlelist.filter(column=column)
    # 标签查询集
    if tag and tag != 'None':
        articlelist = articlelist.filter(tags__name__in=[tag])
    # 查询集排序
    if order == 'total_views':
        articlelist = articlelist.order_by('-total_views')

    # 每页显示 n 篇文章
    paginator = Paginator(articlelist, 5)
    # 获取 url 中的页码
    page = request.GET.get('page')
    # 将导航对象响应的页面内容返回给 articles
    articles = paginator.get_page(page)
    # 需要传递给模板
    context = {'articles': articles, 'order': order, 'search': search, 'column': search,  'tag': tag,}
    # render函数：载入模板，并返回context对象
    return render(request, 'article/list.html', context)


# 文章详情
def article_detail(request, id):
    # 取出相应的文章
    article = ArticlePost.objects.get(id=id)
    # 提取文章评论
    comments = Comment.objects.filter(article=id)
    # 浏览量 +1
    article.total_views += 1
    article.save(update_fields=['total_views'])

    # 将markdown语法渲染成html样式
    md = markdown.Markdown(extensions=[
                                         # 包含 缩写、表格等常用扩展
                                         'markdown.extensions.extra',
                                         # 语法高亮扩展
                                         'markdown.extensions.codehilite',
                                         # 目录扩展
                                         'markdown.extensions.toc',
                                     ])
    article.body = md.convert(article.body)
    # 需要传递给模板的对象
    context = {'article': article, 'toc': md.toc, 'comments': comments}
    # 载入模板，并返回context对象
    return render(request, 'article/detail.html', context)


# 写文章的视图
# 检查登录
@login_required(login_url='/userprofile/login')
def article_create(request):
    # 判断用户是否提交数据
    if request.method == 'POST':
        # 将提交的数据赋值到单表实例中
        article_post_form = ArticlePostForm(request.POST, request.FILES)
        # 判断提交的数据是否满足模型的要求
        if article_post_form.is_valid():
            # 保存数据，单暂时不提交到数据库中
            new_article = article_post_form.save(commit=False)
            # 指定数据库中 id=1 的用户为作者
            # 如果你进行过删除数据表的操作，可能会找不到 id=1 的用户
            # 此时请重新创建用户，并传入此用户的id
            new_article.author = User.objects.get(id=request.user.id)

            if request.POST['column'] != 'none':
                new_article.column = ArticleColumn.objects.get(id=request.POST['column'])
            # 将新文章保存到数据库中
            new_article.save()
            # 保存 tags 的多对多关系       如果提交的表单使用了commit=False选项，则必须调用save_m2m()才能正确的保存标签，就像普通的多对多关系一样。
            article_post_form.save_m2m()
            return redirect("article:article_list")
        # 如果数据不合法，返回错误信息
        else:
            return HttpResponse("表单内容有误，请重新填写。")
    # 如果用户请求获取数据
    else:
        # 创建表单类实例
        article_post_form = ArticlePostForm()
        # 赋值上下文
        columns = ArticleColumn.objects.all()
        context = {'article_post_form': article_post_form, 'column': columns}
        # 返回模板
        return render(request, 'article/create.html', context)


# 删除文章（不安全）
def article_delete(request, id):
    # 根据 id 获得需要删除的文章
    article = ArticlePost.objects.get(id=id)
    # 调用delete()方法删除文章
    article.delete()
    # 完成删除后返回文章列表
    return redirect("article:article_list")


# 安全删除文章
@login_required(login_url='/userprofile/login')
def article_safe_delete(request, id):
    article = ArticlePost.objects.get(id=id)
    if request.user != article.author:
        return HttpResponse("您无权删除本文章")

    if request.method == 'POST':
        article = ArticlePost.objects.get(id=id)
        article.delete()
        return redirect("article:article_list")
    else:
        return HttpResponse("仅允许post请求")


# 更新文章
@login_required(login_url='/userprofile/login')
def article_update(request, id):
    # 获取需要修改的具体文章对象
    article = ArticlePost.objects.get(id=id)
    if request.user != article.author:          # 后端业务逻辑再次验证用户身份
        return HttpResponse("您无权编辑本文章")
    # 判断用户是否为POST提交表单数据
    if request.method == "POST":
        # 将提交的而数据赋值到表单实例中
        article_post_form = ArticlePostForm(data=request.POST)
        # 判断提交的数据是否满足模型需要
        if article_post_form.is_valid():
            if request.POST['column'] != 'none':
                article.column = ArticleColumn.objects.get(id=request.POST['column'])
            else:
                article.column = None
            # 保存新写入的 title、body 数据并保存
            article.title = request.POST['title']
            article.body = request.POST['body']
            article.save()
            # 完成后返回到修改后的文章中。需要传入文章的id值
            return redirect("article:article_detail", id=id)
        # 如果数据不合法，返回错误信息
        else:
            return HttpResponse("表单内容有误，请重新填写。")
    # 如果用户 GET 请求获取数据
    else:
        # 创建表单类实例
        article_post_form = ArticlePostForm()
        columns = ArticleColumn.objects.all()
        # 赋值上下文，将 article 文章对象也传递进去，以便提取旧的内容
        context = {'article': article, 'article_post_form': article_post_form, 'column': columns, }
        # 将响应返回到模板中
        return render(request, 'article/update.html', context)


class ContextMixin:
    """
    Mixin
    """
    def get_context_data(self, **kwargs):
        # 获取原有的上下文
        context = super().get_context_data(**kwargs)
        # 增加新上下文
        context['order'] = 'total_views'
        return context


class ArticleListView(ContextMixin, ListView):
    """
    文章列表类视图
    """
    # 查询集的名称
    context_object_name = 'articles'
    # 模板
    template_name = 'article/list.html'

    def get_queryset(self):
        """
        查询集
        """
        queryset = ArticlePost.objects.filter(title='Python')
        return queryset


class ArticleDetailView(DetailView):
    """
    文章详情类视图
    """
    queryset = ArticlePost.objects.all()
    context_object_name = 'article'
    template_name = 'article/detail.html'

    def get_object(self):
        """
        获取需要展示的对象
        """
        # 首先调用父类的方法
        obj = super(ArticleDetailView, self).get_object()
        # 浏览量 +1
        obj.total_views += 1
        obj.save(update_fields=['total_views'])
        return obj


class ArticleCreateView(CreateView):
    """
    创建文章的类视图
    """
    model = ArticlePost
    fields = '__all__'
    # 或者有选择的提交字段，比如：
    # fields = ['title']
    template_name = 'article/create_by_class_view.html'
