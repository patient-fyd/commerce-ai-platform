-- CommerceAI 源数据库：规范化 OLTP 模型。
-- 业务实体：用户、分类、SPU、SKU。
-- 业务过程：下单、支付、退款。

SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE TABLE user_info (
    user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户内部主键',
    user_no VARCHAR(32) NOT NULL COMMENT '稳定的业务用户编号',
    user_name VARCHAR(100) NOT NULL COMMENT '用户显示名称',
    mobile VARCHAR(20) NOT NULL COMMENT '示例业务使用的手机号码',
    email VARCHAR(255) NULL COMMENT '可选邮箱地址',
    user_status TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '用户状态：0=禁用，1=正常',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '用户账户创建时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '用户记录最近修改时间',
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_user_info_user_no (user_no),
    UNIQUE KEY uk_user_info_mobile (mobile),
    UNIQUE KEY uk_user_info_email (email),
    CONSTRAINT chk_user_info_status CHECK (user_status IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='注册用户';

CREATE TABLE category_info (
    category_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '分类内部主键',
    parent_category_id BIGINT UNSIGNED NULL COMMENT '父分类主键；NULL 表示根分类',
    category_code VARCHAR(32) NOT NULL COMMENT '稳定的业务分类编码',
    category_name VARCHAR(100) NOT NULL COMMENT '分类显示名称',
    category_level TINYINT UNSIGNED NOT NULL COMMENT '分类层级，根分类从 1 开始',
    sort_order INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '同级分类内的显示顺序',
    category_status TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '分类状态：0=禁用，1=正常',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '分类创建时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '分类记录最近修改时间',
    PRIMARY KEY (category_id),
    UNIQUE KEY uk_category_info_code (category_code),
    KEY idx_category_info_parent (parent_category_id),
    CONSTRAINT fk_category_info_parent FOREIGN KEY (parent_category_id) REFERENCES category_info (category_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT chk_category_info_level CHECK (category_level >= 1),
    CONSTRAINT chk_category_info_status CHECK (category_status IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='层级商品分类';

CREATE TABLE spu_info (
    spu_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'SPU 内部主键',
    category_id BIGINT UNSIGNED NOT NULL COMMENT '商品概念所属的叶子分类主键',
    spu_code VARCHAR(32) NOT NULL COMMENT '稳定的业务 SPU 编码',
    spu_name VARCHAR(200) NOT NULL COMMENT '不区分销售规格的共享商品名称',
    brand_name VARCHAR(100) NULL COMMENT '商品品牌名称',
    spu_status TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT 'SPU 状态：0=禁用，1=正常',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'SPU 创建时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT 'SPU 记录最近修改时间',
    PRIMARY KEY (spu_id),
    UNIQUE KEY uk_spu_info_code (spu_code),
    KEY idx_spu_info_category (category_id),
    CONSTRAINT fk_spu_info_category FOREIGN KEY (category_id) REFERENCES category_info (category_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT chk_spu_info_status CHECK (spu_status IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='销售规格共享的标准商品单元';

CREATE TABLE sku_info (
    sku_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'SKU 内部主键',
    spu_id BIGINT UNSIGNED NOT NULL COMMENT '该销售规格所属的 SPU 主键',
    sku_code VARCHAR(32) NOT NULL COMMENT '稳定的业务 SKU 编码',
    sku_name VARCHAR(255) NOT NULL COMMENT '包含重要规格的可售商品名称',
    specification_json JSON NULL COMMENT '颜色、容量或尺寸等销售规格属性',
    sale_price DECIMAL(12, 2) NOT NULL COMMENT '当前目录销售价，单位为人民币元；订单明细保留实际成交价',
    sku_status TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT 'SKU 状态：0=禁用，1=正常',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT 'SKU 创建时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT 'SKU 记录最近修改时间',
    PRIMARY KEY (sku_id),
    UNIQUE KEY uk_sku_info_code (sku_code),
    KEY idx_sku_info_spu (spu_id),
    CONSTRAINT fk_sku_info_spu FOREIGN KEY (spu_id) REFERENCES spu_info (spu_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT chk_sku_info_price CHECK (sale_price >= 0),
    CONSTRAINT chk_sku_info_status CHECK (sku_status IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='可独立销售的商品规格';

CREATE TABLE order_info (
    order_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单内部主键',
    order_no VARCHAR(32) NOT NULL COMMENT '面向业务的唯一订单号',
    user_id BIGINT UNSIGNED NOT NULL COMMENT '下单用户主键',
    order_status TINYINT UNSIGNED NOT NULL COMMENT '订单状态：10=待支付，20=已支付，30=已完成，40=已取消',
    order_amount DECIMAL(12, 2) NOT NULL COMMENT '订单总金额，单位为人民币元；应等于订单明细金额之和',
    ordered_at DATETIME(3) NOT NULL COMMENT '用户提交订单的时间',
    cancelled_at DATETIME(3) NULL COMMENT '订单取消时间，不适用时为 NULL',
    completed_at DATETIME(3) NULL COMMENT '订单完成时间，不适用时为 NULL',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '订单记录持久化时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '订单记录最近修改时间',
    PRIMARY KEY (order_id),
    UNIQUE KEY uk_order_info_no (order_no),
    KEY idx_order_info_user_time (user_id, ordered_at),
    KEY idx_order_info_status_time (order_status, ordered_at),
    CONSTRAINT fk_order_info_user FOREIGN KEY (user_id) REFERENCES user_info (user_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT chk_order_info_status CHECK (order_status IN (10, 20, 30, 40)),
    CONSTRAINT chk_order_info_amount CHECK (order_amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='订单头，一张用户订单一行';

CREATE TABLE order_detail (
    order_detail_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单明细内部主键',
    order_id BIGINT UNSIGNED NOT NULL COMMENT '所属订单主键',
    sku_id BIGINT UNSIGNED NOT NULL COMMENT '购买的 SKU 主键',
    sku_code_snapshot VARCHAR(32) NOT NULL COMMENT '下单时记录的 SKU 编码快照',
    sku_name_snapshot VARCHAR(255) NOT NULL COMMENT '下单时记录的 SKU 名称快照',
    unit_price DECIMAL(12, 2) NOT NULL COMMENT '下单时的成交单价，单位为人民币元',
    quantity INT UNSIGNED NOT NULL COMMENT '本订单明细的购买数量',
    line_amount DECIMAL(12, 2) NOT NULL COMMENT '订单明细金额，单位为人民币元，等于成交单价乘以购买数量',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '订单明细记录持久化时间',
    PRIMARY KEY (order_detail_id),
    UNIQUE KEY uk_order_detail_order_sku (order_id, sku_id),
    KEY idx_order_detail_sku (sku_id),
    CONSTRAINT fk_order_detail_order FOREIGN KEY (order_id) REFERENCES order_info (order_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_order_detail_sku FOREIGN KEY (sku_id) REFERENCES sku_info (sku_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT chk_order_detail_unit_price CHECK (unit_price >= 0),
    CONSTRAINT chk_order_detail_quantity CHECK (quantity > 0),
    CONSTRAINT chk_order_detail_line_amount CHECK (line_amount = unit_price * quantity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='订单明细，一张订单内每种 SKU 一行';

CREATE TABLE payment_info (
    payment_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '支付尝试内部主键',
    payment_no VARCHAR(32) NOT NULL COMMENT '面向业务的唯一支付流水号',
    order_id BIGINT UNSIGNED NOT NULL COMMENT '本次支付对应的订单主键',
    payment_attempt_no SMALLINT UNSIGNED NOT NULL COMMENT '订单内从 1 开始递增的支付尝试序号',
    payment_channel VARCHAR(20) NOT NULL COMMENT '支付渠道：WECHAT、ALIPAY 或 BANK_CARD',
    payment_status TINYINT UNSIGNED NOT NULL COMMENT '支付状态：10=待处理，20=成功，30=失败，40=已关闭',
    payment_amount DECIMAL(12, 2) NOT NULL COMMENT '本次支付尝试金额，单位为人民币元；第一版不支持拆分支付，每次支付尝试应支付完整订单金额',
    third_party_transaction_no VARCHAR(64) NULL COMMENT '支付渠道返回的唯一交易流水号',
    requested_at DATETIME(3) NOT NULL COMMENT '支付尝试发起时间',
    paid_at DATETIME(3) NULL COMMENT '支付渠道确认支付成功的时间',
    closed_at DATETIME(3) NULL COMMENT '失败或主动关闭的支付到达终态的时间',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '支付记录持久化时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '支付记录最近修改时间',
    PRIMARY KEY (payment_id),
    UNIQUE KEY uk_payment_info_no (payment_no),
    UNIQUE KEY uk_payment_info_order_attempt (order_id, payment_attempt_no),
    UNIQUE KEY uk_payment_info_provider_txn (third_party_transaction_no),
    CONSTRAINT fk_payment_info_order FOREIGN KEY (order_id) REFERENCES order_info (order_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT chk_payment_info_attempt CHECK (payment_attempt_no >= 1),
    CONSTRAINT chk_payment_info_channel CHECK (payment_channel IN ('WECHAT', 'ALIPAY', 'BANK_CARD')),
    CONSTRAINT chk_payment_info_status CHECK (payment_status IN (10, 20, 30, 40)),
    CONSTRAINT chk_payment_info_amount CHECK (payment_amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='支付尝试，包含未成功的尝试记录';

CREATE TABLE refund_info (
    refund_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '退款请求内部主键',
    refund_no VARCHAR(32) NOT NULL COMMENT '面向业务的唯一退款申请号',
    order_id BIGINT UNSIGNED NOT NULL COMMENT '包含退款明细的订单主键',
    order_detail_id BIGINT UNSIGNED NOT NULL COMMENT '本次退款申请对应的订单明细主键',
    payment_id BIGINT UNSIGNED NOT NULL COMMENT '本次退款原路退回所引用的成功支付主键',
    refund_status TINYINT UNSIGNED NOT NULL COMMENT '退款状态：10=待处理，20=成功，30=失败，40=已取消',
    refund_quantity INT UNSIGNED NOT NULL COMMENT '本次退款请求申请的商品数量',
    refund_amount DECIMAL(12, 2) NOT NULL COMMENT '本次退款请求申请的金额，单位为人民币元',
    refund_reason VARCHAR(255) NOT NULL COMMENT '本次退款请求的可读原因',
    third_party_refund_no VARCHAR(64) NULL COMMENT '支付渠道返回的唯一退款流水号',
    requested_at DATETIME(3) NOT NULL COMMENT '退款请求发起时间',
    refunded_at DATETIME(3) NULL COMMENT '支付渠道确认退款成功的时间',
    closed_at DATETIME(3) NULL COMMENT '失败或取消的退款到达终态的时间',
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '退款记录持久化时间',
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '退款记录最近修改时间',
    PRIMARY KEY (refund_id),
    UNIQUE KEY uk_refund_info_no (refund_no),
    UNIQUE KEY uk_refund_info_provider_no (third_party_refund_no),
    KEY idx_refund_info_order_time (order_id, requested_at),
    KEY idx_refund_info_detail (order_detail_id),
    KEY idx_refund_info_payment (payment_id),
    CONSTRAINT fk_refund_info_order FOREIGN KEY (order_id) REFERENCES order_info (order_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_refund_info_detail FOREIGN KEY (order_detail_id) REFERENCES order_detail (order_detail_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_refund_info_payment FOREIGN KEY (payment_id) REFERENCES payment_info (payment_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT chk_refund_info_status CHECK (refund_status IN (10, 20, 30, 40)),
    CONSTRAINT chk_refund_info_quantity CHECK (refund_quantity > 0),
    CONSTRAINT chk_refund_info_amount CHECK (refund_amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='退款请求，一次退款请求一行';
